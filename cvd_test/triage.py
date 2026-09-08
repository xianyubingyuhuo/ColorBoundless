# -*- coding: utf-8 -*-
"""triage：6.15 测评流程状态机——分诊引擎 + 用户档案汇总（project.md 6.13/6.15）

职责边界（与既有模块分工）：
    grid_test.build_profile 测试2 三维阈值 → 档案的定量字段（职责单一，保持不动）
    triage.triage_stage0 Stage 0 快筛结果 → [绿]/[黄]/[红] 分流 + 红旗 + 处方（6.15 判定表）
    triage.triage_full Stage 1+2 完整结果 → 复诊（放行 build 档案 or 转深度加测）
    triage.build_user_profile 多源证据 → 完整 UserColorProfile（type 投票+severity+confidence）

设计要点（全部有 6.15 背书）：
    - 规则引擎而非 LLM 判定：可解释、可复现、防幻觉——Agent 是"测评师"不是"出题人"，
      Agent 拿本模块输出做话术与主观融合，不参与判定本身
    - 非对称代价：[红] 任一红旗即触发（漏检代价 > 多测代价）；[黄] 是兜底桶
    - 档位语义（grid_test.LEVELS）：index 0 = Δ 最大最易档，final level 越高视觉越好
    - severity 映射为工程起点（对照正常收敛档 5~7），上线前用真人数据校准（同 LEVELS 模式）
"""
import numpy as np

from . import grid_test
from .grid_test import DIM_C, DIM_H, DIM_L, LEVELS

# 分诊级别（对外常量，Agent/UI 按名字分支）
LEVEL_FAST = "fast" # [绿] 快速通道：粗档案 → 直接试色
LEVEL_STANDARD = "standard" # [黄] 标准：补完测试2/3 → build 档案
LEVEL_DEEP = "deep" # [红] 深度：Stage 1+2 + 处方加测
LEVEL_DONE = "done" # 复诊通过：可以 build 档案

# 快筛版 runner 工厂参数（6.15：每维 3 轮阶梯、只探档位不收敛）
SCREEN_ROUNDS = 3
SCREEN_START_LEVEL = 0 # 从最易档起（快筛要"轻松开场"）
# 判定表档位门槛（快筛 3 轮从 0 爬：全对 → 3；卡 2 = 中间；≤1 = 重度嫌疑）
SCREEN_GOOD = 3 # ≥ 此档 → [绿] 候选
SCREEN_HEAVY = 1 # ≤ 此档 → [红] 红旗
# 完整版（12 轮）重度门槛：打满轮数仍停在低档
FULL_HEAVY = 2
# severity 映射：mean final level ≥ 此值 → 0；≤ 0 → 1（工程起点，待真人校准）
SEVERITY_REF_LEVEL = 5.0


def make_screen_runners(seed=None):
    """Stage 0 快筛用三维度 runner（3 轮、无反转收敛要求）"""
    return {dim: grid_test.ThresholdRunner(
        dim, start_level=SCREEN_START_LEVEL,
        n_reversals=99, max_rounds=SCREEN_ROUNDS, seed=seed)
        for dim in (DIM_L, DIM_C, DIM_H)}


def _run_screen(runners, answer_fn):
    """跑一轮快筛：answer_fn(img, info) → 用户回答位置（UI/模拟用户注入）"""
    final_levels = {}
    for dim, runner in runners.items():
        while not runner.done:
            img, info = runner.next_round()
            runner.submit(answer_fn(img, info))
        final_levels[dim] = int(runner.level)
    return final_levels


def triage_stage0(plates, grid_levels, subjective=False):
    """Stage 0 快筛 → 分诊（6.15 判定表的 Stage 0 部分）

    参数：
        plates [{"kind": "deutan", "correct": bool}, ...] 伪等色图判定
                    （Stage 0 两张分型图：deutan 图 + protan 图）
        grid_levels {DIM_L: final_level, DIM_C: .., DIM_H: ..} 快筛终档(0-based)
        subjective 用户点了"看不清/吃力"（主观信号，Agent 融合入口）
    返回：
        {"level", "flags", "prescriptions", "type_hint", "min_level", "agent_note"}
    """
    flags, prescriptions = [], []
    kinds_wrong = [p["kind"] for p in plates if not p["correct"]]
    min_level = int(min(grid_levels.values()))

    # ---- 红旗判定（任一命中 → [红]，非对称代价）----
    if len(kinds_wrong) == len(plates) and len(plates) > 0:
        flags.append("ishihara_all_wrong")
    if min_level <= SCREEN_HEAVY:
        flags.append("grid_heavy")
    if subjective and min_level < SCREEN_GOOD:
        flags.append("subjective_with_signal")

    # ---- [绿] 快速通道门槛：全部满足 ----
    fast_ok = (not kinds_wrong) and min_level >= SCREEN_GOOD and not subjective

    if flags:
        level = LEVEL_DEEP
        if "ishihara_all_wrong" in flags:
            prescriptions.append("locate") # 6.14 波浪图定位：第三票
        if "grid_heavy" in flags:
            prescriptions.append("matching") # 6.14 匹配反解：重度定量
        if "subjective_with_signal" in flags:
            prescriptions.append("comfort") # Agent 安抚 + 复测
    elif fast_ok:
        level = LEVEL_FAST
    else:
        level = LEVEL_STANDARD

    # 主观信号独立于级别：只要用户诉苦，Agent 就该安抚（6.15 Agent 职责②）
    if subjective and "comfort" not in prescriptions:
        prescriptions.append("comfort")

    # type 粗判（快筛只投票不定案；定案在 build_user_profile 与测试3 交叉）
    if not kinds_wrong:
        type_hint = "normal"
    elif len(kinds_wrong) == 1:
        type_hint = kinds_wrong[0]
    else:
        type_hint = "uncertain"

    notes = {
        LEVEL_FAST: "用户分辨轻松，直接进入试色环节",
        LEVEL_STANDARD: "正常推进完整测评",
        LEVEL_DEEP: "需要更多测试才能给出可靠结论，安抚后继续",
    }[level]
    return {"level": level, "flags": flags, "prescriptions": prescriptions,
            "type_hint": type_hint, "min_level": min_level, "agent_note": notes}


def triage_full(stage0_result, grid_full, hue_result, subjective=False):
    """Stage 1+2 完整结果 → 复诊（放行 build 档案 or 转深度加测，6.15 Stage 3）

    参数：
        stage0_result triage_stage0 的返回（快筛分流记录）
        grid_full {dim: {"final_level": int, "n_reversals": int, "maxed": bool}}
        hue_result hue_test.judge_arrangement 的返回（verdict/total_error/...）
        subjective 主观信号（沿用/更新）
    返回：
        {"level": "done"|"deep", "flags", "prescriptions", "axis_conflict", "agent_note"}
    """
    flags, prescriptions = [], []
    verdict = hue_result["verdict"]
    type_hint = stage0_result["type_hint"]

    # ---- 红旗 1：分型矛盾（测试1 kind vs 测试3 轴向）----
    axis_conflict = False
    if verdict == "unclear":
        flags.append("axis_unclear") # 轴向不可判 → 加定位测试拿第三票
    elif type_hint in ("deutan", "protan") and verdict == "blue-yellow":
        axis_conflict = True
        flags.append("axis_conflict")
    elif type_hint == "normal" and verdict in ("red-green", "blue-yellow"):
        axis_conflict = True
        flags.append("axis_conflict")

    # ---- 红旗 2：阶梯不收敛（数据质量差 → 重跑）----
    not_converged = any(g["maxed"] and g["n_reversals"] < 2
                        for g in grid_full.values())
    if not_converged:
        flags.append("not_converged")

    # ---- 红旗 3：完整版仍重度（12 轮还停在低档）----
    min_full = min(int(g["final_level"]) for g in grid_full.values())
    heavy = min_full <= FULL_HEAVY
    if heavy:
        flags.append("grid_heavy_full")

    if flags:
        level = LEVEL_DEEP
        if "axis_unclear" in flags or "axis_conflict" in flags:
            prescriptions.append("locate")
        if "not_converged" in flags:
            prescriptions.append("rerun_grid")
        if "grid_heavy_full" in flags:
            prescriptions.append("matching")
    else:
        level = LEVEL_DONE
    if subjective:
        prescriptions.append("comfort")

    return {"level": level, "flags": flags, "prescriptions": prescriptions,
            "axis_conflict": axis_conflict,
            "agent_note": ("分诊通过，可生成档案" if level == LEVEL_DONE
                           else "存在红旗，按处方加测后融合")}


def _vote_type(plates, hue_verdict):
    """测试1（隐身图 kind）× 测试3（错误轴 verdict）→ cvd_type 投票

    双证据链（6.9）：一致 → 定案；矛盾 → uncertain（诚实边界：不强行二选一）。
    测试3 只能定轴（red-green vs blue-yellow），亚型（deutan/protan）由隐身图定。
    """
    kinds_wrong = [p["kind"] for p in plates if not p["correct"]]
    if not kinds_wrong:
        if hue_verdict == "normal":
            return "normal", True # 双证据一致：正常
        if hue_verdict == "unclear":
            return "normal", False # 单证据：倾向正常但置信打折
        return "uncertain", False # 隐身图全过却测出轴 → 矛盾（轻度/异常）
    if len(kinds_wrong) > 1:
        # 多张隐身图都错：重度或多型，轴一致时取轴下亚型，否则 uncertain
        if hue_verdict == "red-green" and ("deutan" in kinds_wrong or "protan" in kinds_wrong):
            return ("deutan" if "deutan" in kinds_wrong else "protan"), False
        return "uncertain", False
    kind = kinds_wrong[0]
    if hue_verdict == "unclear":
        return kind, False # 单证据：给型但置信打折
    if (kind in ("deutan", "protan") and hue_verdict == "red-green") \
            or (kind == "tritan" and hue_verdict == "blue-yellow"):
        return kind, True # 双证据一致
    return "uncertain", False # 轴向矛盾


def _severity_from_levels(levels):
    """终档 → severity ∈ [0,1]（工程起点：正常收敛档 5~7 → 0，0 档 → 1）"""
    if not levels:
        return 0.0
    mean_level = float(np.mean(levels))
    return float(np.clip((SEVERITY_REF_LEVEL - mean_level) / SEVERITY_REF_LEVEL, 0.0, 1.0))


def build_user_profile(plates, grid_results, hue_result,
                       triage_path, deep_results=None, hold_out=None):
    """多源证据 → 完整 UserColorProfile（6.9 档案结构 + 6.13 分诊字段）

    参数：
        plates [{"kind","correct"}...] 全部伪等色图判定（快筛+加测合并）
        grid_results {DIM_L/C/H: ThresholdRunner}（完整版 runner；快筛通道也可传）
        hue_result judge_arrangement 返回
        triage_path "fast"/"standard"/"deep"
        deep_results 可选 {"locate": ..., "matching": ...} 深度加测结果（当前仅计入一致性）
        hold_out 可选 {"hit_rate": float} 6.12 验证闭环结果
    返回：
        UserColorProfile dict
    """
    thresholds = grid_test.build_profile(grid_results)
    verdict = hue_result["verdict"]
    cvd_type, consistent = _vote_type(plates, verdict)

    final_levels = [int(r.level) for r in grid_results.values()]
    severity = 0.0 if cvd_type == "normal" else _severity_from_levels(final_levels)

    # ---- 置信度：证据一致性打分（诚实边界：封顶 0.95，不给 1.0）----
    conf = 0.5
    if consistent:
        conf += 0.25
    elif cvd_type == "uncertain":
        conf -= 0.15
    if deep_results:
        conf += 0.10 # 深度加测提供了额外证据
    if hold_out and hold_out.get("hit_rate", 0.0) >= 0.8:
        conf += 0.15 # hold-out 验证通过（6.12）
    confidence = float(np.clip(conf, 0.2, 0.95))

    return {
        "cvd_type": cvd_type,
        "severity": round(severity, 3),
        "dL_threshold": thresholds["dL_threshold"],
        "dC_threshold": thresholds["dC_threshold"],
        "dH_threshold": thresholds["dH_threshold"],
        "triage_path": triage_path,
        "confidence": round(confidence, 2),
        "hold_out": hold_out,
        "evidence": {
            "n_plates": len(plates),
            "hue_verdict": verdict,
            "hue_total_error": hue_result["total_error"],
            "final_levels": {d: int(r.level) for d, r in grid_results.items()},
            "consistent": consistent,
        },
    }

