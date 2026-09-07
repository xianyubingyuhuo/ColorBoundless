# -*- coding: utf-8 -*-
"""大脑客户端：OpenAI 兼容协议的最薄封装。

只做一件事：把 messages(+tools) 发给当前 provider，把 message 拿回来。
不流式、不重试、不存历史——会话状态归 FastAPI 层管。
错误不穿透：失败走 _error 字段（中文、说人话），永不 raise。
"""
import json
import urllib.error
import urllib.request

from config import current_provider


def llm_chat(messages, tools=None, tool_choice=None, timeout=60, max_tokens=4096):
    """def 8 · 一次对话补全调用。

    入参：messages = [{"role": "system"|"user"|"assistant"|"tool", "content": ...}]
          tools / tool_choice = OpenAI function calling 格式，原样透传
          max_tokens = 上限。注意它包含推理型模型的思维链 token——
          GLM-5.3-flash 思维链约 1000~2000 tokens，给小了正文会被截成空
          （实测 max_tokens=1024 时 finish=length 且 content=''）。
    出参（形状统一，永不 raise）：
          {"role": "assistant", "content": str|None,
           "tool_calls": [...] 仅当模型请求调工具,
           "_error": None | 中文说明,
           "_usage": {"prompt_tokens", "completion_tokens", "total_tokens"}}
    """
    p = current_provider()
    payload = {"model": p["model"], "messages": messages, "max_tokens": max_tokens}
    if tools:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice

    req = urllib.request.Request(
        p["base_url"],
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + p["api_key"],
                 "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:200]
        return {"role": "assistant", "content": None,
                "_error": f"HTTP {e.code}: {detail}", "_usage": None}
    except Exception as e:
        return {"role": "assistant", "content": None,
                "_error": f"网络异常: {e}", "_usage": None}

    msg = data["choices"][0]["message"]
    msg.pop("reasoning_content", None)      # 思维链不上屏，保持 JSON 契约干净
    msg["_error"] = None
    msg["_usage"] = data.get("usage")
    return msg
