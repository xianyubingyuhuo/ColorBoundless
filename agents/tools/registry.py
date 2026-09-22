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
from agents.tools.foundation_search import foundation_search_tool
from agents.tools.navigate import navigate_tool, PAGES
from agents.tools.vision_profile import get_vision_profile_tool
from agents.tools.recommend_shade import recommend_shade_tool   # def 18 · 色号回填通路
from agents.tools.shade_review import shade_review_tool         # def 27 · 选色社会视角守门
from agents.prompt import TOOL_DESCRIPTIONS      # def 22k · 工具描述话术收拢至 prompt.py

_REGISTRY = {
    "search_shade_tool": {
        "fn": search_shade_tool,
        "schema": {
            "type": "function",
            "function": {
                "name": "search_shade_tool",
                "description": TOOL_DESCRIPTIONS["search_shade_tool"],
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
    "foundation_search_tool": {
        "fn": foundation_search_tool,
        "schema": {
            "type": "function",
            "function": {
                "name": "foundation_search_tool",
                "description": TOOL_DESCRIPTIONS["foundation_search_tool"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string",
                                  "description": "需求描述，如'黄黑皮想要自然提亮的底妆'"},
                        "brand": {"type": "string",
                                  "enum": ["Maybelline", "Lancôme", "Make Up For Ever", "L'Oréal"],
                                  "description": "限定集团品牌，不限定则省略"},
                        "shade_level": {"type": "string",
                                        "enum": ["light", "medium", "deep"],
                                        "description": "按明度档过滤：light=白皙/浅肤色，medium=自然/中等肤色，deep=小麦/深肤色"},
                        "top_k": {"type": "integer", "description": "返回数量，默认 3"},
                    },
                    "required": ["query"],
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
                "description": TOOL_DESCRIPTIONS["navigate_tool"],
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
                "description": TOOL_DESCRIPTIONS["get_vision_profile_tool"],
                "parameters": {"type": "object", "properties": {}},
            },
        },
    },
    "recommend_shade_tool": {
        "fn": recommend_shade_tool,
        "schema": {
            "type": "function",
            "function": {
                "name": "recommend_shade_tool",
                "description": TOOL_DESCRIPTIONS["recommend_shade_tool"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "parts": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 5,
                            "description": "推荐清单，每项 {region, hex}；一个部位一项，最多 5 项",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "region": {"type": "string",
                                               "enum": ["lip", "foundation", "eyeshadow", "brow", "blush"],
                                               "description": "试妆部位"},
                                    "hex": {"type": "string",
                                            "description": "推荐色值，6 位 hex（如 FF4D6D）"},
                                },
                                "required": ["region", "hex"],
                            },
                        },
                        "reason": {"type": "string",
                                   "description": "一句话推荐思路，如'日常通勤妆：豆沙色为主'"}
                    },
                    "required": ["parts"],
                },
            },
        },
    },
    "shade_review_tool": {   # def 27 · 选色社会视角守门
        "fn": shade_review_tool,
        "schema": {
            "type": "function",
            "function": {
                "name": "shade_review_tool",
                "description": TOOL_DESCRIPTIONS["shade_review_tool"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "raw_hex": {"type": "string",
                                    "description": "用户提到的色值，支持 #FF4D6D / f46 等写法"},
                        "region": {"type": "string",
                                   "enum": ["lip", "foundation", "eyeshadow", "brow", "blush"],
                                   "description": "试妆部位/品类"},
                    },
                    "required": ["raw_hex", "region"],
                },
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