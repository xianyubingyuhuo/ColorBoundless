# -*- coding: utf-8 -*-
"""def 17a · 色盲测评会话服务——cvd_test 引擎（selftest 22/22 背书）的 HTTP 化封装。

会话状态机（MVP 12 题版，题目序列固定）：
    Q1-Q2   石原分型图（deutan / protan 各一张）→ 用户报数字
    Q3-Q11  网格找异色块（DIM_L/C/H 三维 × 各 3 轮快筛阶梯）→ 用户点异色块 (row,col)
    Q12     色相渐变排列（15 块打乱，用户按平滑渐变顺序点击）→ judge_arrangement
    收卷    triage_stage0 分诊（fast/standard/deep）→ build_user_profile 出档案

铁律（与 cvd_test 设计要点同源）：
    判定全部由 cvd_test 规则引擎完成（规则而非 LLM：可解释、可复现、防幻觉），
    Agent 是"测评师"不是"出题人"——AI 只引用档案 JSON 组织话术，不参与判定。
边界（MVP 诚实声明）：
    - deep 红旗的处方加测（波浪定位/匹配反解）暂不实现，deep 档案按保守口径标注
    - 主观信号（"看不清/吃力"勾选）暂不采集，triage 的 subjective=False
    - 单用户 MVP：档案存全局最新一份（_PROFILE），多用户留待产品化
"""
import base64
import json
import math
import time
import uuid
from pathlib import Path

import cv2
import numpy as np

from cvd_test import grid_test, hue_test, ishihara, triage
from cvd_test.grid_test import DIM_C, DIM_H, DIM_L

SCREEN_ROUNDS = 3   # 快筛：每维 3 轮（与 triage.make_screen_runners 一致）
HUE_N = 15          # 排列测试色块数（与 D-15 量级一致）
EXAM_TTL = 60 * 30  # 会话 30 分钟超时

_EXAMS = {}    # exam_id -> 会话状态
_PROFILE = {}  # 全局最新档案（单用户 MVP）

# def 26 · 档案持久化：_PROFILE 原为纯内存态，后端重启即丢——前端还渲染着旧档案、
# AI 工具与校色端点却报「尚无测评档案」，用户被迫重测 22 题（def 24/25 两次踩坑）。
# 落盘后：测评一次终身有效，重启自动恢复，AI 读取 / 校色 / 试妆校正通道不再断链。
_PROFILE_PATH = Path(__file__).resolve().parent / "_cvd_profile.json"


def _save_profile() -> None:
    """档案落盘（失败不阻断主流程：内存态仍可用于本次进程）。"""
    try:
        _PROFILE_PATH.write_text(
            json.dumps(_PROFILE, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _load_profile() -> None:
    """启动时恢复上次测评档案（文件缺失/损坏则静默跳过 = 全新状态）。"""
    try:
        if _PROFILE_PATH.exists():
            data = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("cvd_type"):
                cal = data.get("calibration")
                if isinstance(cal, dict):
                    # def 34 · 启停位归一：旧档案无 enabled → 按 mode!=off 推导
                    # （拆分前 mode 兼任启停：correct/simulate 即视为开启）
                    cal.setdefault("enabled", cal.get("mode", "off") != "off")
                _PROFILE.clear()
                _PROFILE.update(data)
    except Exception:
        pass


_load_profile()


def reset_profile() -> None:
    """def 50 · 后端重启即清档案（用户 2026-09-22：重启 = 全新演示态）。
    与 def 26「落盘保活」的分工：落盘解决的是进程崩溃恢复（运行中断链）；
    reset 由启动钩子 main.lifespan 显式调用——每次重启归零，测评从头演示。"""
    _PROFILE.clear()
    try:
        if _PROFILE_PATH.exists():
            _PROFILE_PATH.unlink()
    except Exception:
        pass


def _img_b64(img) -> str:
    """RGB uint8 ndarray → PNG base64（前端 <img src="data:image/png;base64,...">）"""
    ok, buf = cv2.imencode(".png", img[:, :, ::-1])   # RGB→BGR 后编码
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _gc():
    """超时会话清理（防内存缓涨）"""
    now = time.time()
    for k in [k for k, v in _EXAMS.items() if now - v["created"] > EXAM_TTL]:
        _EXAMS.pop(k, None)


def _start() -> dict:
    exam_id = uuid.uuid4().hex[:12]
    state = {
        "exam_id": exam_id,
        "created": time.time(),
        "q_no": 0,                    # 已答题数（0-based 决定阶段）
        "stage": "ishihara",
        "runners": triage.make_screen_runners(),   # 三维快筛 runner（阶梯法有状态）
        "plates": [],                 # [{"kind","correct"}] 石原判定
        "hue_data": [],               # [{perm, rgbs}] 两道排列的题面数据
        "hue_results": [],            # 两道排列的判分结果
        "wave_result": None,          # 波段定位佐证
        "subjective": False,
        "pending": None,              # 当前待答题元信息
    }
    _EXAMS[exam_id] = state
    _gc()
    return state


def _ih_sheets():
    """石原 10 题：deutan×4 + protan×4 + tritan×2（三轴全覆盖——红绿两型之外补蓝黄轴盲区，
    用户 2026-09-19 反馈"缺蓝绿测试数据"），数字 0-9 每次随机配对（make_plate 内点阵随机，
    同 digit 不同 seed 图面也不同）——消除"总是那几道相同题目"的重复感"""
    rng = np.random.default_rng()
    digits = [int(d) for d in rng.permutation(10)]
    kinds = ["deutan", "protan", "deutan", "protan", "tritan",
             "deutan", "protan", "deutan", "protan", "tritan"]
    return list(zip(kinds, digits))


# 排列 2 道：全环 + 蓝黄重点半环（第二道专探 blue-yellow 轴）
HUE_SETS = [(0.0, 360.0), (90.0, 270.0)]


def _judge_wave(click_ratio, h_true):
    """色彩波段定位判定（新增题型）：点击比例 → 色相角误差 + 轴向提示。

    诚实边界：单题误差含噪声（屏幕色差/手抖），仅作类型佐证写入档案证据，
    不进入 _vote_type 主投票——主判定仍由石原×排列双证据链完成。
    """
    h_click = (float(click_ratio) % 1.0) * 360.0
    ang = (h_click - h_true + 180.0) % 360.0 - 180.0          # [-180, 180)
    rad = math.radians(ang)
    if abs(math.cos(rad)) >= 0.7:
        axis = "red-green"
    elif abs(math.sin(rad)) >= 0.7:
        axis = "blue-yellow"
    else:
        axis = "mixed"
    # 容差分级（用户 2026-09-13 反馈：目测有色差，判定放宽）——佐证用途，不进主投票
    if abs(ang) <= 15.0:
        match = "match"          # 吻合（容差内）
    elif abs(ang) <= 35.0:
        match = "close"          # 接近（滑动对比后的正常精度）
    else:
        match = "deviate"        # 明显偏差（轴向信号）
    return {"h_true": round(h_true, 1), "h_click": round(h_click, 1),
            "ang_err": round(ang, 1), "axis_hint": axis, "match": match,
            "note": "拖动对比交互 + 容差分级；单题仅作类型佐证，不进主投票"}


def _next_question(state: dict) -> dict:
    """推进到下一题并生成题面。返回 results（含 question / done / profile）

    题库结构（2026-09-11 扩充：每类 ≥10、排列 2 道、新增波段定位；2026-09-19 石原补三轴）：
        Q1-Q10   石原分型图（deutan×4 + protan×4 + tritan×2，数字 0-9 洗牌，点阵随机）
        Q11-Q19  网格找异色（DIM_L/C/H × 各 3 轮快筛阶梯；每轮 base 色随机 → 无重复感）
        Q20-Q21  色相渐变排列（全环 1 道 + 蓝黄半环 1 道，拖拽排序）
        Q22      色彩波段定位（目标色 → 在波段条上指出位置，轴向佐证）
    """
    total = 22
    q = state["q_no"]

    # ---- Q1-Q10 石原分型图 ----
    if q < 10:
        state["stage"] = "ishihara"
        kind, digit = _ih_sheets()[q]
        img, _info = ishihara.make_plate(digit, kind=kind, severity=1.0, size=360)
        state["pending"] = {"type": "ishihara", "kind": kind, "digit": str(digit)}
        return {"stage": state["stage"], "question_no": q + 1, "question_total": total,
                "question": {"type": "ishihara", "img_b64": _img_b64(img),
                             "prompt": f"第 {q + 1} 张：这张圆点图里你看到什么数字？（看不清就填 0）"},
                "done": False}

    # ---- Q11-Q19 网格找异色块（三维度严格分开测，各 3 轮快筛）----
    if q < 19:
        state["stage"] = "grid"
        dim = (DIM_L, DIM_C, DIM_H)[(q - 10) // SCREEN_ROUNDS]
        runner = state["runners"][dim]
        img, info = runner.next_round()
        state["pending"] = {"type": "grid", "dim": dim}
        return {"stage": state["stage"], "question_no": q + 1, "question_total": total,
                "question": {"type": "grid", "img_b64": _img_b64(img),
                             "n": info["n"],
                             "prompt": "哪一块颜色和其他不一样？直接点它。"},
                "done": False}

    # ---- Q20-Q21 色相渐变排列（2 道：全环 / 蓝黄半环）----
    if q < 21:
        state["stage"] = "hue"
        seq = q - 19
        h0, h1 = HUE_SETS[seq]
        rgbs, hues, c_used = hue_test.make_hue_sequence(HUE_N, h_start=h0, h_end=h1)
        perm = [int(p) for p in np.random.default_rng().permutation(HUE_N)]
        state.setdefault("hue_data", []).append({"perm": perm, "rgbs": rgbs.tolist()})
        state["pending"] = {"type": "hue", "seq": seq}
        label = "全色相环" if seq == 0 else "蓝黄重点段"
        return {"stage": state["stage"], "question_no": q + 1, "question_total": total,
                "question": {"type": "hue",
                             "colors": [[int(v) for v in rgbs[p]] for p in perm],
                             "prompt": f"排列 {seq + 1}/2（{label}）：把打乱的色块拖进槽位，"
                                       "按你觉得最平滑的渐变顺序排好。"},
                "done": False}

    # ---- Q22 色彩波段定位（新增题型）----
    if q < 22:
        state["stage"] = "wave"
        rng = np.random.default_rng()
        h_true = float(rng.uniform(0.0, 360.0))
        from cvd_test.color_diff import lab2srgb
        rgb_t = lab2srgb(np.array([62.0, 30.0 * math.cos(math.radians(h_true)),
                                   30.0 * math.sin(math.radians(h_true))]))
        segs = []                                   # 波段条 36 段：Lab 同域生成（L=62/C=30 均匀色相）
        for i in range(36):
            hh = math.radians(i * 10.0)
            segs.append([int(v) for v in lab2srgb(np.array([62.0, 30.0 * math.cos(hh),
                                                            30.0 * math.sin(hh)]))])
        state["pending"] = {"type": "wave", "h_true": h_true}
        return {"stage": state["stage"], "question_no": q + 1, "question_total": total,
                "question": {"type": "wave",
                             "target": [int(v) for v in rgb_t],
                             "segments": segs,
                             "prompt": "看上方目标色块。在下面的色彩波段条上，点击你认为与目标色相同的位置。"},
                "done": False}

    # ---- 收卷 ----
    return _finish(state)


def _answer(state: dict, answer):
    """收卷当前题（题号 +1），更新引擎状态"""
    p = state.get("pending") or {}
    t = p.get("type")
    state["q_no"] += 1

    if t == "ishihara":
        correct = str(answer).strip() == p["digit"]
        state["plates"].append({"kind": p["kind"], "correct": bool(correct)})

    elif t == "grid":
        runner = state["runners"][p["dim"]]
        try:
            pos = (int(answer[0]), int(answer[1]))    # [row, col]
        except Exception:
            pos = (0, 0)                              # 坏答案按 (0,0) 收，阶梯自动放宽
        runner.submit(pos)

    elif t == "hue":
        seq = p["seq"]
        data = state["hue_data"][seq]
        perm = data["perm"]
        rgbs = np.array(data["rgbs"], dtype=np.uint8)
        try:
            disp = [int(v) for v in answer]           # 槽位顺序 = 色块下标序列
            user_order = [perm[k] for k in disp]      # 位置 k 放的原始块 index
        except Exception:
            user_order = list(range(len(perm)))       # 坏答案按未排序收
        state.setdefault("hue_results", []).append(hue_test.judge_arrangement(user_order, rgbs))

    elif t == "wave":
        try:
            ratio = float(answer)                     # 点击位置占波段条比例（0~1）
        except Exception:
            ratio = 0.0
        state["wave_result"] = _judge_wave(ratio, p["h_true"])

    state["pending"] = None


def _finish(state: dict) -> dict:
    """收卷：triage 分诊 → build_user_profile 出档案（判定全部由 cvd_test 规则引擎完成）"""
    state["stage"] = "done"
    grid_levels = {dim: int(r.level) for dim, r in state["runners"].items()}

    tri = triage.triage_stage0(state["plates"], grid_levels, state["subjective"])

    hrs = state.get("hue_results") or []
    if hrs:
        verdicts = [h.get("verdict") for h in hrs]
        # 两道排列：verdict 一致取第一道；不一致取 total_error 更大者（暴露更充分）
        hue_main = hrs[0] if len(set(verdicts)) == 1 else max(hrs, key=lambda h: h.get("total_error", 0.0))
    else:                                             # 防御兜底（正常流程必答）
        hue_main = hue_test.judge_arrangement(list(range(HUE_N)),
                                              np.array([[128, 128, 128]] * HUE_N, dtype=np.uint8))
        verdicts = [hue_main.get("verdict")]

    profile = triage.build_user_profile(
        state["plates"], state["runners"], hue_main, tri["level"])
    profile["evidence"]["hue_verdicts"] = verdicts       # 两道排列的判定链
    profile["evidence"]["wave"] = state.get("wave_result")  # 波段定位佐证（新增题型）

    profile["prescriptions"] = tri.get("prescriptions", [])
    profile["agent_note"] = tri.get("agent_note", "")
    if tri["level"] == triage.LEVEL_DEEP:
        profile["advice"] = "存在多项红旗信号，本档案按保守口径处理；建议线下做深度色觉检查。"
    elif tri["level"] == triage.LEVEL_STANDARD:
        profile["advice"] = "存在部分信号，档案可信度中等，可稍后重测一次复核。"
    else:
        profile["advice"] = "快筛通道通过，档案可直接用于后续校色与推荐。"

    state["profile"] = profile
    _PROFILE.clear()
    _PROFILE.update(profile)                          # 全局最新档案（单用户 MVP）
    _save_profile()                                   # def 26 · 落盘（重启不丢）
    return {"stage": "done", "done": True, "profile": profile}


# ---------------------------------------------------------------------------
# 对外三接口（main.py 端点直接调用）
# ---------------------------------------------------------------------------
def start_exam() -> dict:
    """开新测评会话 → 返回第一题"""
    state = _start()
    return {"ok": True, "tool": "cvd_exam", "query": {"exam_id": state["exam_id"]},
            "results": _next_question(state)}


def answer_exam(exam_id: str, answer) -> dict:
    """收卷当前题 → 返回下一题 / done+档案"""
    state = _EXAMS.get(exam_id)
    if not state:
        return {"ok": False, "tool": "cvd_exam",
                "error": "测评会话不存在或已超时（30 分钟），请重新开始", "results": {}}
    _answer(state, answer)
    return {"ok": True, "tool": "cvd_exam", "query": {"exam_id": exam_id},
            "results": _next_question(state)}


def get_profile() -> dict:
    """最新测评档案（AI 引导与校色的数据源，AI 只引用不心算）"""
    if not _PROFILE:
        return {"ok": False, "tool": "cvd_exam",
                "error": "尚无测评档案，请先在色盲校验页完成测评", "results": {}}
    return {"ok": True, "tool": "cvd_exam", "query": {"source": "最新测评档案"},
            "results": _PROFILE}


def calibrate(mode: str = None, enabled=None) -> dict:
    """校色确认（def 34 · 配置导入与启停拆分，用户 2026-09-21 定稿）。

    两个前端入口职责分离：
      档案页模式按钮（校色/模拟/关闭）= 只导入配置：传 mode，写 mode 不改 enabled，
          不直接驱动页面配色（导入 ≠ 开启）；
      顶部「校色配色」开关 = 唯一启停控制：传 enabled，写 enabled 不改 mode，
          on 时全站按当前配置上色，off 恢复原色。
    mode：
        "correct"  校色模式——试妆时用户所选色号反解为标准视觉等意色（R-06 全站联动同源）
        "simulate" 模拟模式——全站配色按该用户视角模拟展示（共情演示），试妆色号不反解
        "off"      关闭动作（def 35）：只把 enabled 置 False，已导入的配置原样保留；
                   mode=off 仅作为「从未导入过配置」的历史数据存在，此时开开关 → 升级 correct
    enabled：None=不改启停位（纯导入）；True/False=开关切启停（mode 保持不变）。
    消费方口径：试妆反解 = mode=="correct" 且 enabled（main.py 同步）；
    theme_cvd 自动恢复同口径（enabled 为 False 不上色）。
    """
    if not _PROFILE:
        return {"ok": False, "tool": "cvd_exam",
                "error": "尚无测评档案，请先完成测评再做校色选择", "results": {}}
    cal_old = _PROFILE.get("calibration") or {}
    if enabled is None:
        if mode not in ("correct", "simulate", "off"):
            return {"ok": False, "tool": "cvd_exam",
                    "error": f"未知校色模式: {mode}（可选 correct/simulate/off）", "results": {}}
        if mode == "off":
            # def 35 · 「关闭」= 只关启停：enabled=False，已导入的配置原样保留
            # （旧版把 mode 写成 off 导致关了再开配置丢失——用户 2026-09-21 反馈）
            mode = cal_old.get("mode", "off")
            new_enabled = False
        else:
            new_enabled = bool(cal_old.get("enabled", False))   # 纯导入：启停位保持现状
    else:
        mode = cal_old.get("mode", "off")                   # 启停切换：配置不动
        if bool(enabled) and mode == "off":
            mode = "correct"                                # 无配置时开开关 → 默认 correct
        new_enabled = bool(enabled)
    _PROFILE["calibration"] = {
        "mode": mode,
        "kind": _PROFILE.get("cvd_type"),
        "severity": _PROFILE.get("severity"),
        "enabled": new_enabled,
        "updated": int(time.time()),
    }
    _save_profile()   # def 26 · 校色状态一并落盘（刷新/重启后恢复如前）
    return {"ok": True, "tool": "cvd_exam",
            "query": {"mode": mode, "enabled": new_enabled},
            "results": {"calibration": _PROFILE["calibration"],
                        "advice": _PROFILE.get("advice", "")}}
