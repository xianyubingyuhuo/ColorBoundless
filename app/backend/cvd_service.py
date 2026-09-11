# -*- coding: utf-8 -*-
"""def 14 · cvd_service：色盲视角 API 服务层（模拟预览 + 色对校验，五件套契约）。

为什么独立成层？
    cvd_test/* 是纯算法（numpy，无 Web 依赖）；本层负责：
    ① hex 字符串解析/输出（前端只传 #RRGGBB）
    ② 前端友好类型名 → 模型 kind 映射（deuteranopia → deutan）
    ③ 规则库加载与命中判定（data/knowledge_base/cvd_rules/rules.json，
       avoid/safe pairs 已由 cvd_test/selftest 模拟器闭环校准）
    ④ 五件套输出 + 异常不穿透（tryon_service 同款纪律）

数字口径（答辩注意）：
    verdict 阈值 confuse<5 / risky<12 为项目启发式（与 selftest 的
    safe_pairs “ΔE>5 可辨” 同源），非行业标准，勿引用为文献结论；
    模拟模型为 Machado et al. 2009（Viénot 1999 真人实验背书）。
"""
import json
from pathlib import Path

import numpy as np

from cvd_test.cvd_matrix import simulate_cvd
from cvd_test.color_diff import ciede2000, lab2srgb, srgb2lab

_ROOT = Path(__file__).resolve().parents[2]
_RULES_PATH = _ROOT / "data" / "knowledge_base" / "cvd_rules" / "rules.json"

_RULES = None  # 模块级缓存：规则库只有 4 条，读一次即可

# 前端友好名 → cvd_matrix 模型 kind
_KIND_MAP = {
    "protanopia": "protan",
    "deuteranopia": "deutan",
    "tritanopia": "tritan",
}


def _h2rgb(hex_str):
    """hex → (3,) uint8。宽容解析：可带 #、大小写、3 位缩写。"""
    h = str(hex_str).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6 or any(c not in "0123456789abcdefABCDEF" for c in h):
        raise ValueError(f"hex 格式不对: {hex_str}（需要 #RRGGBB，如 #FF4D6D）")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.uint8)


def _rgb2hex(rgb):
    """(3,) uint8 → '#RRGGBB'（大写）。"""
    return "#{:02X}{:02X}{:02X}".format(*(int(v) for v in rgb))


def _fail(tool, err):
    """五件套错误壳（异常不穿透）。"""
    return {"ok": False, "tool": tool, "error": str(err), "results": {}}


def _load_rules():
    global _RULES
    if _RULES is None:
        _RULES = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    return _RULES


def _norm_pair(pair):
    """规则库色对 → 无序 frozenset（大写归一），便于命中比较。"""
    a, b = pair
    return frozenset((a.strip().upper(), b.strip().upper()))


def preview_hex(hex_color, cvd_type="deuteranopia", severity=1.0):
    """单色模拟预览：正常人看到的颜色 vs 该色觉缺陷用户看到的等效颜色。

    返回五件套；results 含模拟后 hex、ΔE、明度 L 变化（protan 红色塌陷可直接看到）。
    """
    tool = "cvd_preview"
    try:
        t = str(cvd_type).lower()
        kind = _KIND_MAP.get(t)
        if kind is None:
            raise ValueError(f"未知色觉类型: {cvd_type}（可选 {sorted(_KIND_MAP)}）")
        sev = float(np.clip(float(severity), 0.0, 1.0))
        rgb = _h2rgb(hex_color)
        sim = simulate_cvd(rgb, kind, sev)
        lab_o, lab_s = srgb2lab(rgb), srgb2lab(sim)
        return {
            "ok": True,
            "tool": tool,
            "query": {"hex": _rgb2hex(rgb), "cvd_type": t,
                      "severity": round(sev, 2), "model": "Machado 2009"},
            "results": {
                "original_hex": _rgb2hex(rgb),
                "simulated_hex": _rgb2hex(sim),
                "delta_e": round(float(ciede2000(lab_o, lab_s)), 2),
                "luminance": {
                    "original": round(float(lab_o[0]), 1),
                    "simulated": round(float(lab_s[0]), 1),
                    "drop": round(float(lab_o[0] - lab_s[0]), 1),
                },
            },
        }
    except Exception as exc:  # 错误不穿透（五件套契约）
        return _fail(tool, exc)


def check_pair(hex_a, hex_b, cvd_type="deuteranopia"):
    """色对校验：正常 ΔE vs 该缺陷（完全型）下 ΔE + 规则库命中（avoid/safe）。

    代码裁判（数字说话）：
        dE_sim < 5   → confuse        （该用户几乎看不出两色区别）
        dE_sim < 12  → risky          （勉强可辨，建议加大明度差）
        否则         → distinguishable
        阈值为项目启发式（selftest safe_pairs 同源），非行业标准。
    """
    tool = "cvd_check"
    try:
        t = str(cvd_type).lower()
        kind = _KIND_MAP.get(t)
        if kind is None:
            raise ValueError(f"未知色觉类型: {cvd_type}（可选 {sorted(_KIND_MAP)}）")
        rgb_a, rgb_b = _h2rgb(hex_a), _h2rgb(hex_b)
        sim_a = simulate_cvd(rgb_a, kind, 1.0)
        sim_b = simulate_cvd(rgb_b, kind, 1.0)
        dE_normal = float(ciede2000(srgb2lab(rgb_a), srgb2lab(rgb_b)))
        dE_sim = float(ciede2000(srgb2lab(sim_a), srgb2lab(sim_b)))
        contraction = round(100.0 * (1.0 - dE_sim / dE_normal), 1) if dE_normal > 1e-9 else 0.0

        # 规则库命中：同类型规则的 avoid/safe pairs（无序比较）
        rule_hit, rule_id, action = "none", None, ""
        want = _norm_pair((_rgb2hex(rgb_a), _rgb2hex(rgb_b)))
        for rule in _load_rules():
            if rule.get("cvd_type") != t:
                continue
            if any(_norm_pair(p) == want for p in rule.get("avoid_pairs", [])):
                rule_hit, rule_id = "avoid", rule["rule_id"]
                action = rule.get("recommended_action", "")
                break
            if any(_norm_pair(p) == want for p in rule.get("safe_pairs", [])):
                rule_hit, rule_id = "safe", rule["rule_id"]
                break

        if dE_sim < 5.0:
            verdict = "confuse"
        elif dE_sim < 12.0:
            verdict = "risky"
        else:
            verdict = "distinguishable"
        return {
            "ok": True,
            "tool": tool,
            "query": {"hex_a": _rgb2hex(rgb_a), "hex_b": _rgb2hex(rgb_b),
                      "cvd_type": t, "model": "Machado 2009"},
            "results": {
                "a_hex": _rgb2hex(rgb_a), "a_sim_hex": _rgb2hex(sim_a),
                "b_hex": _rgb2hex(rgb_b), "b_sim_hex": _rgb2hex(sim_b),
                "dE_normal": round(dE_normal, 2),
                "dE_sim": round(dE_sim, 2),
                "contraction_pct": contraction,
                "verdict": verdict,
                "rule_hit": rule_hit,
                "rule_id": rule_id,
                "recommended_action": action,
            },
        }
    except Exception as exc:  # 错误不穿透
        return _fail(tool, exc)


# ---------------------------------------------------------------------------
# def 17b · 试妆校色：按测评档案反解"标准视觉等意色"
# ---------------------------------------------------------------------------
def recover_true_color(rgb_seen, kind, severity):
    """用户"看到的颜色" → 反解最接近的标准视觉真实色（试妆上妆用）。

    产品语义：色盲用户挑选色号时，TA 眼中的"正红"在标准视觉下可能是偏棕的；
    上妆前把 TA 的选择映射回"标准视觉下的等意色"，TA 上脸后的效果才符合预期，
    且他人看到的也是社会共识下的那个颜色。

    数学事实（诚实边界）：Machado 矩阵对二色视存在信息简并（多个真实色映射到
    同一 seen 色），严格逆映射不存在——此处取 **Lab 空间最小改动解**（坐标下降
    + 步长减半，目标 = 模拟后与 seen 的 ΔE00 最小），语义即"校正幅度最小、
    且在该用户眼中观感与所选一致的真实颜色"。
    """
    rgb_seen = np.asarray(rgb_seen, dtype=np.uint8)
    lab_seen = srgb2lab(rgb_seen)

    lab = srgb2lab(rgb_seen).astype(float)      # 初值：seen 本身
    step = np.array([6.0, 8.0, 8.0])            # L/a/b 初始步长（CIE 单位）

    def loss(lab_v):
        rgb_t = lab2srgb(np.clip(lab_v, 0, 255))
        sim = simulate_cvd(rgb_t, kind, severity)
        return ciede2000(srgb2lab(sim), lab_seen)

    best = loss(lab)
    for _ in range(24):                          # 坐标下降 + 步长减半
        improved = False
        for axis in range(3):
            for sign in (1.0, -1.0):
                cand = lab.copy()
                cand[axis] += sign * step[axis]
                val = loss(cand)
                if val < best - 1e-4:
                    lab, best, improved = cand, val, True
        if not improved:
            step = step / 2.0
            if float(np.max(step)) < 0.25:
                break

    rgb_true = np.clip(lab2srgb(np.clip(lab, 0, 255)), 0, 255).astype(np.uint8)
    residual = float(ciede2000(srgb2lab(simulate_cvd(rgb_true, kind, severity)), lab_seen))
    return rgb_true, round(residual, 2)


def correct_hex_for_profile(hex_color: str, profile: dict):
    """按测评档案把用户所选 hex 校正为标准视觉等意色。

    参数：
        hex_color 已清洗的 #RRGGBB（用户所选）
        profile   色觉档案 dict（cvd_exam.get_profile 的 results；可为 None）
    返回：
        (corrected_hex | None, info | None)——不需要校正时 (None, None)
    规则（诚实边界，宁缺毋滥）：
        normal / uncertain / 档案缺失 → 不校正（uncertain=证据矛盾，强行校正反而失真）；
        仅 deutan/protan/tritan 且 severity>0 才校正。
    """
    if not profile:
        return None, None
    cvd_type = str(profile.get("cvd_type", "")).lower()
    if cvd_type not in ("deutan", "protan", "tritan"):
        return None, None
    sev = float(profile.get("severity", 0.0) or 0.0)
    if sev <= 0.0:
        return None, None

    rgb_seen = _h2rgb(hex_color)
    rgb_true, residual = recover_true_color(rgb_seen, cvd_type, sev)
    corrected = _rgb2hex(rgb_true)
    if corrected.upper() == _rgb2hex(rgb_seen).upper():
        return None, None                        # 反解回原色 = 无需校正

    info = {
        "applied": True,
        "original_hex": _rgb2hex(rgb_seen),
        "corrected_hex": corrected,
        "cvd_type": cvd_type,
        "severity": round(sev, 2),
        "delta_e_residual": residual,            # 校正后在该用户眼中与所选的残差（越小越保真）
        "source": "cvd_exam profile",
    }
    return corrected, info
