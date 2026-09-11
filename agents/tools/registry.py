# -*- coding: utf-8 -*-
"""工具注册表 —— 大脑（LLM）与手（工具①②③）之间的总机。

职责：
    get_tools_schema(): 把三件工具的 function calling 描述交给大脑（什么名、干什么、要什么参数）
    dispatch_tool():    按名字分发调用；未知工具/坏参数/内部异常一律兜底成五件套 JSON
边界：
    不做对话循环（那是 app/backend/agent_loop 的事），只做"名字 → 函数 → JSON"。
    LLM 给的参数名以这里 schema 为准，与各工具真实签名逐一核对（raw_hex/text）。
"""
import json

from agents.tools.search_shade import search_shade_tool
from agents.tools.kb_search import kb_search_tool
from agents.tools.palette_search import palette_search_tool, HUE_GROUPS
from agents.tools.navigate import navigate_tool, PAGES
from agents.tools.vision_profile import get_vision_profile_tool

_REGISTRY = {
    "search_shade_tool": {
        "fn": search_shade_tool,
        "schema": {
            "type": "function",
            "function": {
                "name": "search_shade_tool",
                "description": "按用户给出的十六进制色值，从官方口红色号库找最接近的色号，"
                               "返回按色差 dE 升序的候选（含色号名、冷暖调、场合、气质标签）。"
                               "用户提到具体色值（如 #FF4D6D、f46）想找口红色号时用它。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "raw_hex": {"type": "string",
                                    "description": "用户提到的色值，支持 #FF4D6D / f46 / FF4D6D 等写法"},
                        "top_k": {"type": "integer", "description": "返回候选数量，默认 3"},
                    },
                    "required": ["raw_hex"],
                },
            },
        },
    },
    "palette_search_tool": {
        "fn": palette_search_tool,
        "schema": {
            "type": "function",
            "function": {
                "name": "palette_search_tool",
                "description": "在 262,144 色的全色域里找与目标色值最接近的颜色，"
                               "可限定色相族（如只在 red/white 内找）。"
                               "用户想找'接近某颜色的其他颜色'或官方色号库没有的近似色时用它。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "raw_hex": {"type": "string", "description": "目标色值，如 #FF4D6D"},
                        "hue_group": {"type": "string",
                                      "enum": list(HUE_GROUPS),
                                      "description": "限定色相族，不限定则省略"},
                        "top_k": {"type": "integer", "description": "返回数量，默认 5"},
                    },
                    "required": ["raw_hex"],
                },
            },
        },
    },
    "kb_search_tool": {
        "fn": kb_search_tool,
        "schema": {
            "type": "function",
            "function": {
                "name": "kb_search_tool",
                "description": "检索化妆知识库（肤色底调、冷暖皮判断、色彩搭配、选购建议等）。"
                               "知识性、方法性问题先检索再回答，不要凭记忆编。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "检索问句，如'冷白皮怎么选粉底'"},
                        "top_k": {"type": "integer", "description": "返回条数，默认 3"},
                    },
                    "required": ["text"],
                },
            },
        },
    },
    "navigate_tool": {
        "fn": navigate_tool,
        "schema": {
            "type": "function",
            "function": {
                "name": "navigate_tool",
                "description": "把用户引导到网站对应页面（前端会真的跳转，请先想清楚该去哪）。"
                               "各页面职责：palette=选色/查色号/全库找色/配色知识；"
                               "tryon=上传照片虚拟试妆；cvd=色盲自测+色盲视角模拟与校色；"
                               "products=产品库（建设中）；home=网站主页。"
                               "用户表达'想去/带我去/帮我在XX功能里弄'，或当前话题属于某页职责时调用；"
                               "调用后用一句话告诉用户为什么带 TA 去那里。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "string",
                                 "enum": list(PAGES),
                                 "description": "目标页面名"},
                        "reason": {"type": "string",
                                   "description": "一句话引导理由，如'去这里可以做色盲自测'"},
                    },
                    "required": ["page"],
                },
            },
        },
    },
    "get_vision_profile_tool": {
        "fn": get_vision_profile_tool,
        "schema": {
            "type": "function",
            "function": {
                "name": "get_vision_profile_tool",
                "description": "读取用户最近一次色盲测评的色觉档案（类型 cvd_type、严重度 severity、"
                               "明度/彩度/色相三维分辨阈值、置信度、建议 advice）。"
                               "用户做完测评后让你总结结果、解释 TA 的色彩视觉特点、"
                               "或给出个性化用色/校色建议时，先用它读档案再说话，禁止凭空推测。",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    },
}


def get_tools_schema() -> list:
    """def 11a · 三件工具的 function calling 描述（OpenAI 格式，各兼容端通吃）。"""
    return [v["schema"] for v in _REGISTRY.values()]


def dispatch_tool(name: str, arguments: dict) -> dict:
    """def 11b · 按名字调工具。规矩不破：大脑永远收到合法 JSON，异常兜底不穿透。"""
    entry = _REGISTRY.get(name)
    if entry is None:
        return {"ok": False, "tool": name, "error": f"未知工具: {name}", "results": []}
    if not isinstance(arguments, dict):
        arguments = {}
    try:
        return entry["fn"](**arguments)
    except TypeError as e:
        return {"ok": False, "tool": name, "error": f"参数不匹配: {e}", "results": []}
    except Exception as e:
        return {"ok": False, "tool": name, "error": f"工具执行异常: {e}", "results": []}