# -*- coding: utf-8 -*-
"""def 20 · navigate 工具——大脑的"网页调度"轻量工具（一步到位方案，5.6 定稿）。

职责边界：
    只负责"告诉前端该去哪个页面 + 为什么"，不执行任何数据逻辑；
    agent_loop 识别本工具的成功结果后，提升为返回结构顶层的 action 字段，
    前端 chatbox.js 的 doAction() 通道执行真实跳转。
安全阀（铁律同源：路由由 AI 决策，边界由代码守）：
    页面白名单在此硬编码枚举，白名单外的 page 一律拒绝——LLM 给不出第五种去向。
"""

# 页面白名单（key = LLM 用的页面名，value = 前端 URL）
PAGES = {
    "home": "/",
    "palette": "/palette.html",
    "tryon": "/tryon.html",
    "cvd": "/cvd.html",
    "products": "/products.html",
}


def navigate_tool(page: str, reason: str = "") -> dict:
    """引导用户前往指定页面。

    参数：
        page    白名单页面名（home/palette/tryon/cvd/products）
        reason  一句话引导理由（前端轨迹区可见，可解释）
    返回：
        五件套；ok=True 时 results.page_key/url 供 agent_loop 提升 action
    """
    key = (page or "").strip().lower()
    if key not in PAGES:
        return {"ok": False, "tool": "navigate_tool",
                "error": f"未知页面: {page}（可用: {', '.join(PAGES)}）", "results": {}}
    return {"ok": True, "tool": "navigate_tool",
            "query": {"page": key, "reason": reason},
            "results": {"page_key": key, "url": PAGES[key], "reason": reason}}
