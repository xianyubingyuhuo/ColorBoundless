# -*- coding: utf-8 -*-
"""def 11 · 对话循环：大脑选工具 → 代码执行 → 结果喂回 → 直到给出正文。

只认 OpenAI function calling 协议——DeepSeek / 智谱 GLM / 将来的 vLLM 全吃这一套
（R-02 的可插拔性在循环层同样成立）。防失控三件套：MAX_ROUNDS 上限、
发回 API 的消息只含标准字段、工具结果 json.dumps 后走 role=tool 标准通道。

def 22m · 纵深安全防御（用户指令：色库资产绝对不泄露）：
    入口层  _INJECT_PATTERNS  命中即拒答（不调 LLM，确定性 + 零 token）；
    出口层  _LEAK_PATTERNS    LLM 正文扫描，命中即整条替换为拒答话术（兜底越狱/幻觉）。
    工具层  结构性安全：全部检索工具 top_k 钳制、注册表无任何导出/下载类工具。
"""
import json
import re

from agents.prompt import CHAT_SYSTEM
from agents.tools.registry import get_tools_schema, dispatch_tool
from llm_client import llm_chat, llm_chat_stream

MAX_ROUNDS = 5

# ---------------------------------------------------------------------------
# def 22m · 安全常量（正则，re.I 大小写不敏感）
# ---------------------------------------------------------------------------
_REFUSE = "这个问题我不能处理哦。查色号、找接近色、逛功能页面我都很在行，随时吩咐～"

# 入口层：用户消息命中 → 直接拒答（prompt 注入 / 越狱 / 批量导出 / 实现刺探）
_INJECT_PATTERNS = [
    r"忽略.{0,8}(指令|规则|提示|约束)",
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)",
    r"(输出|说出|打印|复述|repeat|show|print)[^。]{0,10}(系统提示|system\s*prompt|你的(初始)?指令)",
    r"(你|您)的(系统提示|初始指令|system\s*prompt)",
    r"(导出|下载|输出|生成|列出|给我|export|download)[^。]{0,14}"
    r"(csv|excel|全部色号|所有色号|整个色库|所有数据|完整数据|数据库|全部内容|整表)",
    r"(色库|色号库|知识库|数据库)[^。]{0,10}(怎么|如何)[^。]{0,6}(导入|导进去|构建|生成|来的)",
    r"(扮演|假装|你现在是)[^。]{0,12}(数据库|文件系统|无限制|不受限)",
]

# 出口层：AI 正文命中（幻觉泄密 / 被 prompt 注入绕过时兜底）
_LEAK_PATTERNS = [
    r"\.csv", r"\.npz", r"\.xlsx", r"download", r"/api/export",
    r"embed_cosmetics_kb", r"vector_store", r"secrets\.local", r"\.env",
    r"llm_[a-z0-9_]*api_key", r"[0-9a-f]{32}\.[0-9a-z]{8,}",
    r"sk-[a-z0-9]{8}", r"glm-[\w.]+", r"deepseek-v[\w.]+",
    r"[a-z]:\\+(users|windows)", r"system\s*prompt",
]


def _sanitize(text):
    """def 22m · 出口扫描：正文命中敏感模式 → 整条替换为拒答话术（只对 AI 正文，误伤极低）。"""
    if not text:
        return text
    for pat in _LEAK_PATTERNS:
        if re.search(pat, text, flags=re.I):
            return _REFUSE
    return text


def _lift_action(action, name, result):
    """def 20/18 · 工具成功 → 顶层调度指令提升（navigate 跳页 / recommend_shade 回填）。

    同一回复可多次调用，取最后一次（同一 action 槽）——agent_reply 与
    agent_reply_stream 共用，避免两份逻辑漂移。
    """
    if name == "navigate_tool" and result.get("ok"):
        r = result.get("results") or {}
        return {"type": "navigate", "page": r.get("url") or "/",
                "page_key": r.get("page_key"), "reason": r.get("reason") or ""}
    if name == "recommend_shade_tool" and result.get("ok"):
        r = result.get("results") or {}
        return {"type": "fill", "parts": r.get("parts") or [],
                "reason": r.get("reason") or ""}
    return action


def _run_tool_call(c):
    """单次工具调用：解析参数 → dispatch → 返回 (args, result)。坏参数兜底空参。"""
    try:
        args = json.loads(c["function"]["arguments"] or "{}")
    except json.JSONDecodeError:
        args = {}
    return args, dispatch_tool(c["function"]["name"], args)


def agent_reply(user_message: str, history: list = None) -> dict:
    """def 11c · 一问到底：能调工具就调，调完喂回，正文出来为止。

    返回 {"content": 正文|None, "error": None|人话, "steps": [工具轨迹], "usage": 累计token}
    steps 给前端展示"大脑动了哪只手"——答辩演示透明度用。

    def 22m · 入口安检：user_message 命中注入/导出/刺探模式 → 不调 LLM 直接拒答。
    """
    for pat in _INJECT_PATTERNS:
        if re.search(pat, user_message or "", flags=re.I):
            return {"content": _REFUSE, "error": None, "steps": [],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "action": None}

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
            return {"content": _sanitize(m.get("content")), "error": None, "steps": steps,
                    "usage": usage, "action": action}

        # 清洗成标准字段再发回（剥掉 index/_usage 等非协议字段，兼容端不挑食）
        clean = [{"id": c.get("id"), "type": "function",
                  "function": {"name": c["function"]["name"],
                               "arguments": c["function"]["arguments"]}}
                 for c in tc]
        messages.append({"role": "assistant", "content": m.get("content"), "tool_calls": clean})

        for c in clean:
            args, result = _run_tool_call(c)
            steps.append({"tool": c["function"]["name"], "args": args, "ok": result.get("ok")})
            action = _lift_action(action, c["function"]["name"], result)
            messages.append({"role": "tool", "tool_call_id": c.get("id") or "",
                             "content": json.dumps(result, ensure_ascii=False)})

    return {"content": None, "error": f"工具调用超过 {MAX_ROUNDS} 轮仍未收敛",
            "steps": steps, "usage": usage, "action": action}


def agent_reply_stream(user_message: str, history: list = None):
    """def 29 · agent_reply 的流式版：yield 事件字典，供 /api/chat/stream（SSE）逐帧下发。

    事件序列（前端按 type 渲染）：
        {"type": "delta", "text"}                     正文增量（逐字上屏）
        {"type": "tool",  "tool", "args", "ok"}       一次工具调用执行完成（轨迹实时可见）
        {"type": "replace", "text"}                   出口安检命中——前端把已流出的正文整条替换
        {"type": "done",  content/error/steps/usage/action}   收尾，payload 与 /api/chat 完全一致
    纪律同 agent_reply：入口安检、MAX_ROUNDS 上限、出口 _sanitize（流式下全文攒完再扫，
    命中发 replace——防泄密的硬门不因流式绕过）。非流式 agent_reply 保留：内部调用
    （测评后自动总结等）与回退路径继续用它。
    """
    for pat in _INJECT_PATTERNS:
        if re.search(pat, user_message or "", flags=re.I):
            yield {"type": "done", "content": _REFUSE, "error": None, "steps": [],
                   "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                   "action": None}
            return

    messages = [{"role": "system", "content": CHAT_SYSTEM}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    tools = get_tools_schema()
    steps = []
    action = None
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    for _ in range(MAX_ROUNDS):
        yield {"type": "status",
               "text": ("大脑思考中…" if not steps
                        else f"大脑思考中…（已完成 {len(steps)} 次工具调用）")}
        text, calls = "", None
        for ev in llm_chat_stream(messages, tools=tools):
            t = ev["type"]
            if t == "delta":
                text += ev["text"]
                yield ev
            elif t == "ping":
                yield ev                       # 心跳透传（前端重置看门狗）
            elif t == "tool_calls":
                calls = ev["calls"]
            elif t == "usage":
                for k in usage:
                    usage[k] += (ev["usage"] or {}).get(k) or 0
            elif t == "error":
                yield {"type": "done", "content": None, "error": ev["text"],
                       "steps": steps, "usage": usage, "action": action}
                return

        if not calls:                       # 正文收尾：出口安检后 done
            safe = _sanitize(text)
            if safe != text:
                yield {"type": "replace", "text": safe}
            yield {"type": "done", "content": safe, "error": None,
                   "steps": steps, "usage": usage, "action": action}
            return

        clean = [{"id": c["id"], "type": "function",
                  "function": {"name": c["function"]["name"],
                               "arguments": c["function"]["arguments"]}}
                 for c in calls]
        messages.append({"role": "assistant", "content": text or None, "tool_calls": clean})

        for c in clean:
            args, result = _run_tool_call(c)
            steps.append({"tool": c["function"]["name"], "args": args, "ok": result.get("ok")})
            yield {"type": "tool", "tool": c["function"]["name"],
                   "args": args, "ok": result.get("ok")}
            action = _lift_action(action, c["function"]["name"], result)
            messages.append({"role": "tool", "tool_call_id": c.get("id") or "",
                             "content": json.dumps(result, ensure_ascii=False)})

    yield {"type": "done", "content": None,
           "error": f"工具调用超过 {MAX_ROUNDS} 轮仍未收敛",
           "steps": steps, "usage": usage, "action": action}