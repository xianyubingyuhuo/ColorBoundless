# -*- coding: utf-8 -*-
"""def 11 · 对话循环：大脑选工具 → 代码执行 → 结果喂回 → 直到给出正文。

只认 OpenAI function calling 协议——DeepSeek / 智谱 GLM / 将来的 vLLM 全吃这一套
（R-02 的可插拔性在循环层同样成立）。防失控三件套：MAX_ROUNDS 上限、
发回 API 的消息只含标准字段、工具结果 json.dumps 后走 role=tool 标准通道。
"""
import json

from agents.prompt import CHAT_SYSTEM
from agents.tools.registry import get_tools_schema, dispatch_tool
from llm_client import llm_chat

MAX_ROUNDS = 5


def agent_reply(user_message: str, history: list = None) -> dict:
    """def 11c · 一问到底：能调工具就调，调完喂回，正文出来为止。

    返回 {"content": 正文|None, "error": None|人话, "steps": [工具轨迹], "usage": 累计token}
    steps 给前端展示"大脑动了哪只手"——答辩演示透明度用。
    """
    messages = [{"role": "system", "content": CHAT_SYSTEM}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    tools = get_tools_schema()
    steps = []
    action = None                 # def 20 · navigate 工具成功后提升为顶层调度指令
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    for _ in range(MAX_ROUNDS):
        m = llm_chat(messages, tools=tools)
        u = m.get("_usage") or {}
        for k in usage:
            usage[k] += u.get(k) or 0
        if m.get("_error"):
            return {"content": None, "error": m["_error"], "steps": steps, "usage": usage,
                    "action": None}

        tc = m.get("tool_calls")
        if not tc:                       # 大脑给正文了，循环收敛
            return {"content": m.get("content"), "error": None, "steps": steps,
                    "usage": usage, "action": action}

        # 清洗成标准字段再发回（剥掉 index/_usage 等非协议字段，兼容端不挑食）
        clean = [{"id": c.get("id"), "type": "function",
                  "function": {"name": c["function"]["name"],
                               "arguments": c["function"]["arguments"]}}
                 for c in tc]
        messages.append({"role": "assistant", "content": m.get("content"), "tool_calls": clean})

        for c in clean:
            try:
                args = json.loads(c["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            result = dispatch_tool(c["function"]["name"], args)
            steps.append({"tool": c["function"]["name"], "args": args, "ok": result.get("ok")})
            # def 20 · navigate 成功 → 提升为顶层 action（同一回复可多次调用，取最后一次）
            if c["function"]["name"] == "navigate_tool" and result.get("ok"):
                r = result.get("results") or {}
                action = {"type": "navigate", "page": r.get("url") or "/",
                          "page_key": r.get("page_key"), "reason": r.get("reason") or ""}
            messages.append({"role": "tool", "tool_call_id": c.get("id") or "",
                             "content": json.dumps(result, ensure_ascii=False)})

    return {"content": None, "error": f"工具调用超过 {MAX_ROUNDS} 轮仍未收敛",
            "steps": steps, "usage": usage, "action": action}