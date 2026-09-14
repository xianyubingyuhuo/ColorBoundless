# -*- coding: utf-8 -*-
"""test_prompt：在用提示词资产验证（def 22k 精简版）

测什么：提示词是纯字符串，typo 不会在 import 时暴露——本测试把风险前移：
CHAT_SYSTEM 的工具名与 registry 实际注册一致、无字面花括号（可安全 format）、
TOOL_DESCRIPTIONS 五件齐全且非空。
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
for name in _REGISTRY:
    check(f"提到工具 {name}", name in prompt.CHAT_SYSTEM)

print("== 2. TOOL_DESCRIPTIONS（工具描述话术）==")
check("key 与 registry 注册表完全对齐（防漂移）",
      set(prompt.TOOL_DESCRIPTIONS) == set(_REGISTRY))
for name, text in prompt.TOOL_DESCRIPTIONS.items():
    check(f"{name} 描述非空（>40 字）", len(text) > 40)
    check(f"{name} 无字面花括号", "{" not in text and "}" not in text)

print(f"\n{PASS}/{PASS} assertions passed")
print("ALL GREEN")
