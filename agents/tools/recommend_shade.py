# -*- coding: utf-8 -*-
"""def 18 · recommend_shade 工具——大脑的"色号推荐"结构化出口（回填通路第一棒，5.4 定义）。

职责边界：
    只负责把 AI 给出的"部位+色号"推荐清洗成结构化 JSON，不做任何渲染/存储；
    agent_loop 识别成功结果后提升为顶层 action={type:"fill", parts:[...]}，
    前端 chatbox 的 __cbAction 通道执行回填：tryon 页就地填卡，跨页经 sessionStorage 中转。
安全阀（铁律同源：部位由 AI 给，合法性由代码守）：
    region 白名单硬编码枚举；hex 过 normalize_hex 门卫（与试妆主链路同一把尺）；
    同一部位重复推荐直接拒绝——一个部位一个色，歧义不往下传。
"""
from agents.tools.search_shade import normalize_hex

REGIONS = {"lip", "foundation", "eyeshadow", "brow", "blush"}


def recommend_shade_tool(parts, reason: str = "") -> dict:
    """向用户推荐一组"部位+色号"，前端会自动填入试妆表单（用户可随时微调）。

    参数（LLM 按 schema 给）：
        parts  [{"region": "lip|foundation|eyeshadow|brow|blush", "hex": "FF4D6D"}, ...] 1~5 项
        reason 一句话推荐思路（前端对话区可见，可解释）
    返回：
        五件套；ok=True 时 results.parts = [{"region", "hex"}...]（hex 已门卫清洗，无 # 大写）
    """
    tool = "recommend_shade_tool"
    if not isinstance(parts, list) or not (1 <= len(parts) <= 5):
        return {"ok": False, "tool": tool,
                "error": f"parts 须为 1~5 项的数组，收到 {type(parts).__name__}", "results": {}}
    clean, seen = [], set()
    for i, p in enumerate(parts):
        if not isinstance(p, dict):
            return {"ok": False, "tool": tool,
                    "error": f"第 {i+1} 项须为对象 {{region, hex}}", "results": {}}
        region = str(p.get("region", "")).strip().lower()
        if region not in REGIONS:
            return {"ok": False, "tool": tool,
                    "error": (f"第 {i+1} 项 region 非法: {region!r}"
                              f"（可用: {', '.join(sorted(REGIONS))}）"), "results": {}}
        if region in seen:
            return {"ok": False, "tool": tool,
                    "error": f"region 重复: {region}（每个部位只给一项）", "results": {}}
        try:
            hex_r = normalize_hex(str(p.get("hex", "")))
        except ValueError as e:
            return {"ok": False, "tool": tool, "error": f"第 {i+1} 项色值: {e}", "results": {}}
        clean.append({"region": region, "hex": hex_r})
        seen.add(region)
    return {"ok": True, "tool": tool,
            "query": {"count": len(clean), "reason": reason},
            "results": {"parts": clean, "reason": reason}}
