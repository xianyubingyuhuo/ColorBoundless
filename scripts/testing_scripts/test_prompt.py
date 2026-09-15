# -*- coding: utf-8 -*-
"""test_prompt：在用提示词资产验证（def 23 版）

测什么：CHAT_SYSTEM 与 registry 实际注册对齐、COLOR_KNOWLEDGE 内置知识完整、
无字面花括号（可安全 format）——提示词是纯字符串，typo 不在 import 时暴露。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents import prompt                                           # noqa: E402
from agents.tools.registry import _REGISTRY                         # noqa: E402

PASS = 0


def check(name, cond):
    global PASS
    assert cond, "FAIL: " + name
    PASS += 1
    print("  ok  " + name)


print("== 1. CHAT_SYSTEM（工具台对话 Agent）==")
check("非空且成体系（>600 字）", len(prompt.CHAT_SYSTEM) > 600)
check("无字面花括号（可安全 format）", "{" not in prompt.CHAT_SYSTEM and "}" not in prompt.CHAT_SYSTEM)
check("内置配色知识已拼接", prompt.COLOR_KNOWLEDGE in prompt.CHAT_SYSTEM)
check("说明知识内置不必检索", "内置" in prompt.CHAT_SYSTEM and "不必检索" in prompt.CHAT_SYSTEM)
for name in _REGISTRY:
    check(f"提到工具 {name}", name in prompt.CHAT_SYSTEM)

print("== 2. COLOR_KNOWLEDGE（配色决策原则）==")
check("非空且成体系（>400 字）", len(prompt.COLOR_KNOWLEDGE) > 400)
check("无字面花括号", "{" not in prompt.COLOR_KNOWLEDGE and "}" not in prompt.COLOR_KNOWLEDGE)
for topic in ("肤色底调", "饱和度", "明度", "风格与场合", "质地", "CVD"):
    check(f"覆盖主题 {topic}", topic in prompt.COLOR_KNOWLEDGE)

print("== 3. TOOL_DESCRIPTIONS（工具描述话术）==")
check("key 与 registry 注册表完全对齐（防漂移）",
      set(prompt.TOOL_DESCRIPTIONS) == set(_REGISTRY))
for name, text in prompt.TOOL_DESCRIPTIONS.items():
    check(f"{name} 描述非空（>40 字）", len(text) > 40)
    check(f"{name} 无字面花括号", "{" not in text and "}" not in text)

print(f"\n{PASS}/{PASS} assertions passed")
print("ALL GREEN")
