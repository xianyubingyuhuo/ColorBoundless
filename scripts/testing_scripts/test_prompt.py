# -*- coding: utf-8 -*-
"""test_prompt：提示词资产完整性验证（占位符合法性 + 模拟渲染 + 与 triage 接口对齐）

为什么值得专门测：提示词是纯字符串，typo 不会在 import 时暴露——
占位符拼错要到运行时 format 才炸，且 LangChain 链路里报错点远离根因。
本测试把三类风险前移：字面花括号破坏 format、占位符与引擎字段不一致、
key 与 cvd_test.triage 常量漂移。
"""
import sys
from pathlib import Path
from string import Formatter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents import prompt                                            # noqa: E402
from cvd_test import triage                                          # noqa: E402

PASS = 0


def check(name, cond):
    global PASS
    assert cond, "FAIL: " + name
    PASS += 1
    print("  ok  " + name)


def placeholders(tpl):
    """模板中的字段名集合"""
    return {fn for _, fn, _, _ in Formatter().parse(tpl) if fn}


def renders(tpl, **vals):
    """format 不抛异常 + 所有值真被替换进去（防占位符 typo 成静默字面量）"""
    try:
        out = tpl.format(**vals)
        return all(v in out for v in vals.values())
    except (KeyError, IndexError, ValueError):
        return False


print("== 1. 三个系统提示词 ==")
SYSTEMS = {
    "CVD_DIAGNOSTIC_SYSTEM": prompt.CVD_DIAGNOSTIC_SYSTEM,
    "COLOR_AESTHETICS_SYSTEM": prompt.COLOR_AESTHETICS_SYSTEM,
    "PHOTO_COMPOSITION_SYSTEM": prompt.PHOTO_COMPOSITION_SYSTEM,
}
for name, text in SYSTEMS.items():
    check(f"{name} 非空且成体系（>600 字）", len(text) > 600)
    check(f"{name} 已拼接输出契约", "输出契约" in text)
    check(f"{name} 已拼接 TTS 规则", "TTS 播报规则" in text)
    check(f"{name} 无字面花括号（可安全 format）", "{" not in text and "}" not in text)

print("== 2. TRIAGE_SCRIPTS（分诊话术）==")
check("key 与 triage.LEVEL_* 对齐（防漂移）",
      set(prompt.TRIAGE_SCRIPTS) == {triage.LEVEL_FAST, triage.LEVEL_STANDARD,
                                     triage.LEVEL_DEEP})
# 占位符集合必须与 triage 输出字段一一对应（多一个=KeyError，少一个=话术缺信息）
EXPECT_FIELDS = {
    triage.LEVEL_FAST: {"type_hint"},
    triage.LEVEL_STANDARD: {"type_hint"},
    triage.LEVEL_DEEP: {"flags", "prescriptions"},
}
DUMMY = {"type_hint": "deutan", "flags": "网格重度", "prescriptions": "匹配反解"}
for level, fields in EXPECT_FIELDS.items():
    tpl = prompt.TRIAGE_SCRIPTS[level]
    check(f"{level} 占位符恰为 {sorted(fields)}", placeholders(tpl) == fields)
    check(f"{level} 模拟渲染成功", renders(tpl, **{f: DUMMY[f] for f in fields}))

print("== 3. TEST_GUIDES / COMFORT_SCRIPTS ==")
check("TEST_GUIDES 覆盖三测试 + 6.14 两模式",
      set(prompt.TEST_GUIDES) == {"ishihara", "grid", "hue", "locate", "matching"})
check("COMFORT_SCRIPTS 覆盖主诉/疲劳/重测",
      set(prompt.COMFORT_SCRIPTS) == {"subjective", "fatigue", "retry"})
for group in (prompt.TEST_GUIDES, prompt.COMFORT_SCRIPTS):
    for key, text in group.items():
        check(f"{key} 非空且零占位（直接可用）",
              len(text) > 10 and placeholders(text) == set())

print("== 4. 处方名闭环（triage 处方 → 有话术可讲）==")
check("locate/matching 两个深度处方均有引导话术",
      {"locate", "matching"} <= set(prompt.TEST_GUIDES))
check("comfort 处方有安抚话术", "subjective" in prompt.COMFORT_SCRIPTS)

print("\n%d/%d assertions passed" % (PASS, PASS))
print("ALL GREEN")
