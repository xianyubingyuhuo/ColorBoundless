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
import time
import uuid

import cv2
import numpy as np

from cvd_test import grid_test, hue_test, ishihara, triage
from cvd_test.grid_test import DIM_C, DIM_H, DIM_L

SCREEN_ROUNDS = 3   # 快筛：每维 3 轮（与 triage.make_screen_runners 一致）
HUE_N = 15          # 排列测试色块数（与 D-15 量级一致）
EXAM_TTL = 60 * 30  # 会话 30 分钟超时

_EXAMS = {}    # exam_id -> 会话状态
_PROFILE = {}  # 全局最新档案（单用户 MVP）


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
        "hue": None,                  # {"perm":[...], "rgbs":[[r,g,b]...]}
        "hue_result": None,
        "subjective": False,
        "pending": None,              # 当前待答题元信息
    }
    _EXAMS[exam_id] = state
    _gc()
    return state


def _ih_sheets():
    """石原两题：(混淆轴, 题目数字)——deutan/protan 各一张（triage 双证据链之隐身图票）"""
    return [("deutan", 8), ("protan", 3)]


def _next_question(state: dict) -> dict:
    """推进到下一题并生成题面。返回 results（含 question / done / profile）"""
    total = 12
    q = state["q_no"]

    # ---- Q1-Q2 石原分型图 ----
    if q < 2:
        state["stage"] = "ishihara"
        kind, digit = _ih_sheets()[q]
        img, _info = ishihara.make_plate(digit, kind=kind, severity=1.0, size=360)
        state["pending"] = {"type": "ishihara", "kind": kind, "digit": str(digit)}
        return {"stage": state["stage"], "question_no": q + 1, "question_total": total,
                "question": {"type": "ishihara", "img_b64": _img_b64(img),
                             "prompt": "这张圆点图里你看到什么数字？（看不清就填 0）"},
                "done": False}

    # ---- Q3-Q11 网格找异色块（三维度严格分开测，各 3 轮快筛）----
    if q < 11:
        state["stage"] = "grid"
        dim = (DIM_L, DIM_C, DIM_H)[(q - 2) // SCREEN_ROUNDS]
        runner = state["runners"][dim]
        img, info = runner.next_round()
        state["pending"] = {"type": "grid", "dim": dim}
        return {"stage": state["stage"], "question_no": q + 1, "question_total": total,
                "question": {"type": "grid", "img_b64": _img_b64(img),
                             "n": info["n"],
                             "prompt": "哪一块颜色和其他不一样？直接点它。"},
                "done": False}

    # ---- Q12 色相渐变排列 ----
    if q < 12:
        state["stage"] = "hue"
        rgbs, hues, c_used = hue_test.make_hue_sequence(HUE_N)
        perm = [int(p) for p in np.random.default_rng().permutation(HUE_N)]
        state["hue"] = {"perm": perm, "rgbs": rgbs.tolist()}
        return {"stage": state["stage"], "question_no": q + 1, "question_total": total,
                "question": {"type": "hue",
                             "colors": [[int(v) for v in rgbs[p]] for p in perm],
                             "prompt": "下面 15 个色块是打乱的。按你觉得最平滑的渐变顺序依次点击它们。"},
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
        perm = state["hue"]["perm"]
        rgbs = np.array(state["hue"]["rgbs"], dtype=np.uint8)
        try:
            disp = [int(v) for v in answer]           # 用户点击的显示位顺序
            user_order = [perm[k] for k in disp]      # 位置 k 放的原始块 index
        except Exception:
            user_order = list(range(len(perm)))       # 坏答案按未排序收
        state["hue_result"] = hue_test.judge_arrangement(user_order, rgbs)

    state["pending"] = None


def _finish(state: dict) -> dict:
    """收卷：triage 分诊 → build_user_profile 出档案（判定全部由 cvd_test 规则引擎完成）"""
    state["stage"] = "done"
    grid_levels = {dim: int(r.level) for dim, r in state["runners"].items()}

    tri = triage.triage_stage0(state["plates"], grid_levels, state["subjective"])

    if state.get("hue_result") is None:               # 防御兜底（正常流程 hue 必答）
        rgbs = np.array((state.get("hue") or {}).get("rgbs",
                        [[128, 128, 128]] * HUE_N), dtype=np.uint8)
        state["hue_result"] = hue_test.judge_arrangement(list(range(HUE_N)), rgbs)

    profile = triage.build_user_profile(
        state["plates"], state["runners"], state["hue_result"], tri["level"])

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
