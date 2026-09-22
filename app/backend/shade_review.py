# -*- coding: utf-8 -*-
"""def 27 · 社会视角守门（shade_review）：选色的主流性判定 + 社会等效色翻译 + 主流替代推荐。

产品语义（用户 2026-09-20 定稿，R-08 延伸）：
    校色/试妆的价值不是替用户修正审美，而是三件事——
    ① 如实告知所选颜色在正常人/社会视角下是什么（防「自以为好看出门被笑」的心理伤害）；
    ② 给出「别人看到的效果 ≈ 你想要的效果」的市面在售主流替代
       （correct 反解社会等效色 → 品类在售板按「该用户视角下最接近」排序）；
    ③ 最终决定权在用户：执意原色 → 尊重并走定制；接受推荐 → 推荐色来自在售板，
       若仍无现货直接进定制、不再二次询问。

判定口径（诚实边界）：
    「主流/罕见」无行业标准——以「该品类在售板中与所选色的最小 ΔE2000」为代理
    （在售色 = 市场主款的采样，板越丰代理越准）；罕见阈值 18 为项目启发式，非文献结论。
    仅对已建档且 cvd_type ∈ {deutan, protan, tritan} 且 severity>0 的用户启用拦截
    （正常视觉用户看到的即真实色，无需守门；无档案不拦截、如实返回原因）。
"""
import colorsys

from cvd_test.color_diff import ciede2000, srgb2lab
from cvd_test.cvd_matrix import simulate_cvd
from cvd_service import _h2rgb, _rgb2hex, _fail, correct_hex_for_profile
from cvd_exam import get_profile
from products_service import catalog

_REGION_NAME = {"lip": "唇妆", "foundation": "粉底", "eyeshadow": "眼影",
                "brow": "眉妆", "blush": "腮红"}
_MAINSTREAM_D = 12.0   # ≤12：品类在售板里有相当接近的色 = 主流
_RARE_D = 18.0         # >18：在售板里最近的都差得远 = 罕见/非主流（触发守门确认）


def _hue_name(rgb) -> str:
    """正常视觉下的色相/明度/饱和度中文描述（区间命名：诚实不装精确色名）。"""
    r, g, b = (int(v) / 255.0 for v in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    deg = h * 360.0
    if deg >= 345 or deg < 15:
        hue = "红"
    else:
        # 区间语义：deg ∈ [上一个 hi, hi) → name（如 [95,150) → 绿）
        hue = next(name for hi, name in
                   [(45, "橙"), (70, "黄"), (95, "黄绿"), (150, "绿"), (195, "青"),
                    (255, "蓝"), (290, "紫"), (345, "品红/粉")] if deg < hi)
    tone = "深" if v < 0.35 else ("浅" if v > 0.72 else "中等明度")
    sat = "低饱和（发灰）" if s < 0.18 else ("高饱和（艳）" if s > 0.65 else "中等饱和")
    return f"{hue}调 · {tone} · {sat}"


def shade_review(hex_color: str, region: str) -> dict:
    """选色守门：gate=True 时前端弹确认卡（告知 + 推荐 + 用户决策）。"""
    tool = "shade_review"
    try:
        region = str(region).strip().lower()
        if region not in _REGION_NAME:
            return _fail(tool, f"未知部位: {region}（可选 {sorted(_REGION_NAME)}）")
        rgb = _h2rgb(hex_color)
        hx = _rgb2hex(rgb)

        prof = get_profile()
        if not prof.get("ok"):
            return {"ok": True, "tool": tool, "query": {"hex": hx, "region": region},
                    "results": {"gate": False, "reason": "no_profile",
                                "note": "尚无测评档案——不做社会视角判定，不拦截"}}
        profile = prof["results"]
        kind = str(profile.get("cvd_type", "")).lower()
        sev = float(profile.get("severity", 0.0) or 0.0)

        cat = catalog()
        shades = []
        for it in (cat.get("results", {}).get("items") or []):
            if it.get("category") == region:
                for s in it.get("shades", []):
                    shades.append({"hex": str(s.get("hex", "")).upper().lstrip("#"),
                                   "name": str(s.get("name", "")),
                                   "brand": str(s.get("brand", "") or ""),
                                   "official": bool(s.get("official", False))})
        if not shades:
            return {"ok": True, "tool": tool, "query": {"hex": hx, "region": region},
                    "results": {"gate": False, "reason": "empty_palette",
                                "note": "该品类在售板为空——无法判定主流性，不拦截"}}

        lab_x = srgb2lab(rgb)
        dists = sorted(
            ({"hex": s["hex"], "name": s["name"], "brand": s["brand"],
              "official": s["official"],
              "dE": round(float(ciede2000(lab_x, srgb2lab(_h2rgb(s["hex"])))), 2)}
             for s in shades), key=lambda t: t["dE"])
        min_d = dists[0]["dE"]
        verdict = "mainstream" if min_d <= _MAINSTREAM_D else (
            "uncommon" if min_d <= _RARE_D else "rare")

        gate = bool(min_d > _RARE_D and kind in ("deutan", "protan", "tritan") and sev > 0)
        results = {
            "gate": gate,
            "verdict": verdict,
            "region": region,
            "region_name": _REGION_NAME[region],
            "hex": hx,
            "palette_size": len(shades),
            "min_dE": min_d,
            "nearest": dists[0],
            "seen_by_norm": {"name": _hue_name(rgb), "hex": hx},
            "suggestions": [],
        }

        if gate:
            corrected, corr_info = correct_hex_for_profile(hx, profile)
            if corr_info:
                corr_info["seen_by_norm_name"] = _hue_name(_h2rgb(corr_info["corrected_hex"]))
            results["social_equiv"] = corr_info or {
                "applied": False,
                "note": "所选色反解回自身——正常视角下它就是你看到的样子（罕见但真实）"}

            # 推荐：品类在售板按「该用户视角下与所选色的 ΔE」升序——
            # 语义："换了你看不出区别，别人看到的是正常妆效"
            sim_x = srgb2lab(simulate_cvd(rgb, kind, sev))
            sims = []
            for s in shades:
                d_sim = float(ciede2000(
                    sim_x, srgb2lab(simulate_cvd(_h2rgb(s["hex"]), kind, sev))))
                sims.append((d_sim, s))
            sims.sort(key=lambda t: t[0])
            results["suggestions"] = [
                {"hex": s["hex"], "name": s["name"], "brand": s["brand"],
                 "official": s["official"], "dE_sim": round(d, 2)}
                for d, s in sims[:4]]

        return {"ok": True, "tool": tool,
                "query": {"hex": hx, "region": region,
                          "cvd_type": kind if gate else None,
                          "thresholds": {"mainstream": _MAINSTREAM_D, "rare": _RARE_D}},
                "results": results}
    except Exception as exc:   # 五件套契约：异常不穿透
        return _fail(tool, exc)
