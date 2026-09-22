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


def llm_chat(messages, tools=None, tool_choice=None, timeout=90, max_tokens=4096):
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
    if p.get("thinking") is not None:
        # def 22 · 思考程度透传（GLM 系官方参数 {"type":"disabled"|"enabled"}）：
        # disabled 关掉思维链，首字延迟大幅下降；provider 配置里可按需改。
        payload["thinking"] = p["thinking"]
    if tools:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice

    headers = {"Content-Type": "application/json"}
    if p.get("api_key"):                 # def 44 · 本地服务无鉴权：api_key 留空则不发 Authorization
        headers["Authorization"] = "Bearer " + p["api_key"]
    req = urllib.request.Request(
        p["base_url"],
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
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


def llm_chat_stream(messages, tools=None, tool_choice=None, timeout=90, max_tokens=4096):
    """def 29 · llm_chat 的流式版：SSE 逐块读，yield 事件字典。

    为什么必须有它：非流式下"首字延迟 = 全部生成时间"——GLM flash 档生成
    1500 token 长回复要 40~90s，前端 90s 硬死线必炸（用户全程只看 thinking…）。
    流式后首字 1~2s 上屏，生成时长不再构成等待黑箱。

    入参与 llm_chat 相同；另发 "stream": True。
    出参（事件序列）：
        {"type": "delta",      "text": str}        正文增量（思维链不上屏，跳过）
        {"type": "tool_calls", "calls": [...]}     工具请求（聚合完整后一次性发，clean 格式同非流式）
        {"type": "usage",      "usage": {...}}     token 统计（provider 在收尾 chunk 里带）
        {"type": "error",      "text": str}        出错终止（中文、说人话）
    兼容性：DeepSeek / 智谱 GLM 均为 OpenAI 兼容 SSE（data: {...} 行 + data: [DONE]）。
    tool_calls 分片（arguments 逐段下发）按 index 聚合成完整调用。
    """
    p = current_provider()
    payload = {"model": p["model"], "messages": messages,
               "max_tokens": max_tokens, "stream": True}
    if p.get("thinking") is not None:
        payload["thinking"] = p["thinking"]
    if tools:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice

    headers = {"Content-Type": "application/json",
               "Accept": "text/event-stream"}
    if p.get("api_key"):                 # def 44 · 本地服务无鉴权：api_key 留空则不发 Authorization
        headers["Authorization"] = "Bearer " + p["api_key"]
    req = urllib.request.Request(
        p["base_url"],
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:200]
        yield {"type": "error", "text": f"HTTP {e.code}: {detail}"}
        return
    except Exception as e:
        yield {"type": "error", "text": f"网络异常: {e}"}
        return

    acc = {}                                # tool_calls 分片聚合：index -> {id,name,arguments}
    try:
        with resp:
            for raw in resp:
                line = raw.decode("utf-8", "ignore").strip()
                if not line.startswith("data:"):
                    continue                # SSE 注释/空行跳过
                body = line[5:].strip()
                if body == "[DONE]":
                    break
                try:
                    chunk = json.loads(body)
                except json.JSONDecodeError:
                    continue                # 不完整帧丢弃（流式容错）
                if chunk.get("usage"):
                    yield {"type": "usage", "usage": chunk["usage"]}
                chs = chunk.get("choices") or []
                if not chs:
                    yield {"type": "ping"}          # usage-only 帧也算活着的证据
                    continue
                d = chs[0].get("delta") or {}
                hit = False
                if d.get("content"):
                    yield {"type": "delta", "text": d["content"]}
                    hit = True
                for t in d.get("tool_calls") or []:
                    hit = True
                    i = t.get("index", 0)
                    slot = acc.setdefault(i, {"id": "", "name": "", "arguments": ""})
                    if t.get("id"):
                        slot["id"] = t["id"]
                    fn = t.get("function") or {}
                    if fn.get("name"):
                        slot["name"] = fn["name"]          # name 只在首片
                    if fn.get("arguments"):
                        slot["arguments"] += fn["arguments"]   # arguments 分片拼接
                if not hit or not d.get("content"):
                    # 工具决策轮没有正文 delta——客户端会长时间无帧。回 ping 心跳：
                    # 前端收到即重置看门狗（60s 无任何帧才断）。上游只要活着就有 chunk，
                    # chunk 间隔是秒级，ping 密度足够看门狗永不误杀。
                    yield {"type": "ping"}
    except Exception as e:
        yield {"type": "error", "text": f"流式读取中断: {e}"}
        return

    if acc:
        calls = [{"id": s["id"] or f"call_{i}", "type": "function",
                  "function": {"name": s["name"], "arguments": s["arguments"]}}
                 for i, s in sorted(acc.items())]
        yield {"type": "tool_calls", "calls": calls}
