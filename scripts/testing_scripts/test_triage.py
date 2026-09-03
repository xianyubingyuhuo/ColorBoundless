# -*- coding: utf-8 -*-
"""test_triage：6.15 分诊引擎 + 档案汇总自动验证（规则单测 + 模拟用户端到端）

覆盖：
    1. triage_stage0 判定表（fast/standard/deep + 红旗 + 处方 + 主观信号）
    2. 模拟用户端到端快筛（simulate_user 真跑阶梯 → final level → 分流）
    3. triage_full 复诊（放行 / 轴矛盾 / 不收敛 / 重度 → 处方）
    4. build_user_profile（type 投票一致性/矛盾、severity 单调、confidence 打分）
    5. hue 端到端（severity=0 恒等模拟正常用户 → judge_arrangement → done）
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cvd_test import grid_test, hue_test, triage                     # noqa: E402
from cvd_test.grid_test import DIM_C, DIM_H, DIM_L, LEVELS           # noqa: E402

PASS = 0


def check(name, cond):
    global PASS
    assert cond, "FAIL: " + name
    PASS += 1
    print("  ok  " + name)


PLATES_OK = [{"kind": "deutan", "correct": True},
             {"kind": "protan", "correct": True}]
PLATES_DEUTAN = [{"kind": "deutan", "correct": False},
                 {"kind": "protan", "correct": True}]
PLATES_ALL_WRONG = [{"kind": "deutan", "correct": False},
                    {"kind": "protan", "correct": False}]

print("== 1. triage_stage0 判定表 ==")
r = triage.triage_stage0(PLATES_OK, {DIM_L: 3, DIM_C: 3, DIM_H: 3})
check("fast 分流", r["level"] == triage.LEVEL_FAST)
check("type_hint=normal", r["type_hint"] == "normal")
r = triage.triage_stage0(PLATES_OK, {DIM_L: 2, DIM_C: 3, DIM_H: 3})
check("中档 → standard", r["level"] == triage.LEVEL_STANDARD)
r = triage.triage_stage0(PLATES_ALL_WRONG, {DIM_L: 3, DIM_C: 3, DIM_H: 3})
check("隐身图全错 → deep", r["level"] == triage.LEVEL_DEEP)
check("处方含 locate", "locate" in r["prescriptions"])
check("type_hint=uncertain", r["type_hint"] == "uncertain")
r = triage.triage_stage0(PLATES_OK, {DIM_L: 0, DIM_C: 1, DIM_H: 3})
check("网格重度 → deep", r["level"] == triage.LEVEL_DEEP)
check("处方含 matching", "matching" in r["prescriptions"])
r = triage.triage_stage0(PLATES_OK, {DIM_L: 3, DIM_C: 4, DIM_H: 3}, subjective=True)
check("仅主诉 → standard（保底）", r["level"] == triage.LEVEL_STANDARD)
r = triage.triage_stage0(PLATES_OK, {DIM_L: 2, DIM_C: 2, DIM_H: 2}, subjective=True)
check("主诉+指标差 → deep", r["level"] == triage.LEVEL_DEEP)
check("处方含 comfort", "comfort" in r["prescriptions"])

print("== 2. 模拟用户端到端快筛 ==")
# 正常用户：JND 在第 5 档量级（dL 2.2 / dC 3.0 / dH 5.0），几乎不失误
runners = triage.make_screen_runners(seed=11)
for dim, jnd in ((DIM_L, LEVELS[DIM_L][5]), (DIM_C, LEVELS[DIM_C][5]),
                 (DIM_H, LEVELS[DIM_H][5])):
    grid_test.simulate_user(runners[dim], jnd, p_correct=0.98)
levels_norm = {d: int(r.level) for d, r in runners.items()}
r = triage.triage_stage0(PLATES_OK, levels_norm)
check("正常用户 final levels ≥3: " + str(levels_norm),
      min(levels_norm.values()) >= triage.SCREEN_GOOD)
check("正常用户 → fast", r["level"] == triage.LEVEL_FAST)

# 重度用户：连最易档都看不见（true_delta 超出量程）
runners = triage.make_screen_runners(seed=11)
for dim in (DIM_L, DIM_C, DIM_H):
    grid_test.simulate_user(runners[dim], 99.0, p_correct=0.95)
levels_heavy = {d: int(r.level) for d, r in runners.items()}
r = triage.triage_stage0(PLATES_OK, levels_heavy)
check("重度用户 final levels ≤1: " + str(levels_heavy),
      max(levels_heavy.values()) <= triage.SCREEN_HEAVY)
check("重度用户 → deep + matching", r["level"] == triage.LEVEL_DEEP
      and "matching" in r["prescriptions"])

print("== 3. triage_full 复诊 ==")
grid_ok = {d: {"final_level": 6, "n_reversals": 4, "maxed": False}
           for d in (DIM_L, DIM_C, DIM_H)}
stage0_std = triage.triage_stage0(PLATES_OK, {DIM_L: 2, DIM_C: 3, DIM_H: 3})
hue_norm = {"verdict": "normal", "total_error": 0}
r = triage.triage_full(stage0_std, grid_ok, hue_norm)
check("干净结果 → done", r["level"] == triage.LEVEL_DONE)
hue_rg = {"verdict": "red-green", "total_error": 40}
stage0_deutan = triage.triage_stage0(PLATES_DEUTAN, {DIM_L: 3, DIM_C: 3, DIM_H: 3})
r = triage.triage_full(stage0_deutan, grid_ok, hue_rg)
check("deutan 嫌疑 + red-green 轴一致 → done", r["level"] == triage.LEVEL_DONE)
hue_by = {"verdict": "blue-yellow", "total_error": 40}
r = triage.triage_full(triage.triage_stage0(PLATES_DEUTAN, {DIM_L: 3, DIM_C: 3, DIM_H: 3}),
                       grid_ok, hue_by)
check("deutan 嫌疑 vs blue-yellow 轴矛盾 → deep", r["level"] == triage.LEVEL_DEEP)
check("矛盾处方含 locate", "locate" in r["prescriptions"])
check("axis_conflict 标记", r["axis_conflict"])
grid_nc = {d: {"final_level": 5, "n_reversals": 1, "maxed": True}
           for d in (DIM_L, DIM_C, DIM_H)}
r = triage.triage_full(stage0_std, grid_nc, hue_norm)
check("不收敛 → deep + rerun_grid", r["level"] == triage.LEVEL_DEEP
      and "rerun_grid" in r["prescriptions"])
grid_heavy = {d: {"final_level": 1, "n_reversals": 4, "maxed": False}
              for d in (DIM_L, DIM_C, DIM_H)}
r = triage.triage_full(stage0_std, grid_heavy, hue_norm)
check("完整版重度 → deep + matching", r["level"] == triage.LEVEL_DEEP
      and "matching" in r["prescriptions"])

print("== 4. build_user_profile 档案汇总 ==")


def make_full_runners(seed, jnd_scale=1.0):
    """完整版三维 runner + 模拟用户跑到收敛"""
    out = {}
    for i, dim in enumerate((DIM_L, DIM_C, DIM_H)):
        runner = grid_test.ThresholdRunner(dim, seed=None if seed is None else seed + i)
        grid_test.simulate_user(runner, LEVELS[dim][5] * jnd_scale, p_correct=0.95)
        out[dim] = runner
    return out


hue_norm_result = {"verdict": "normal", "total_error": 2}
prof = triage.build_user_profile(PLATES_OK, make_full_runners(21),
                                 hue_norm_result, triage_path="standard")
check("normal 类型", prof["cvd_type"] == "normal")
check("normal severity=0", prof["severity"] == 0.0)
check("阈值字段齐", all(prof[k] is not None for k in
                        ("dL_threshold", "dC_threshold", "dH_threshold")))
check("一致性置信加成 (conf=%.2f)" % prof["confidence"],
      prof["confidence"] >= 0.7)

# deutan 双证据一致：隐身图 deutan 错 + 排列轴 red-green；重度阈值
prof_d = triage.build_user_profile(
    PLATES_DEUTAN, make_full_runners(22, jnd_scale=4.0),
    {"verdict": "red-green", "total_error": 45}, triage_path="deep",
    deep_results={"locate": {"hit": True}})
check("deutan 定型", prof_d["cvd_type"] == "deutan")
check("deutan severity>0 (%.2f)" % prof_d["severity"], prof_d["severity"] > 0.3)
check("deutan 置信 ≥ normal 基线 (conf=%.2f)" % prof_d["confidence"],
      prof_d["confidence"] >= 0.75)

# 冲突：deutan 嫌疑 vs blue-yellow 轴 → uncertain + 低置信
prof_c = triage.build_user_profile(
    PLATES_DEUTAN, make_full_runners(23),
    {"verdict": "blue-yellow", "total_error": 40}, triage_path="deep")
check("冲突 → uncertain", prof_c["cvd_type"] == "uncertain")
check("冲突置信 < 一致置信 (%.2f)" % prof_c["confidence"],
      prof_c["confidence"] < prof_d["confidence"])

# severity 单调：重度（JND 放大 6 倍）> 中度（2 倍）
prof_sev_heavy = triage.build_user_profile(
    PLATES_DEUTAN, make_full_runners(24, jnd_scale=6.0),
    {"verdict": "red-green", "total_error": 60}, triage_path="deep")
prof_sev_mid = triage.build_user_profile(
    PLATES_DEUTAN, make_full_runners(25, jnd_scale=2.0),
    {"verdict": "red-green", "total_error": 25}, triage_path="standard")
check("severity 单调: heavy(%.2f) > mid(%.2f)" % (
      prof_sev_heavy["severity"], prof_sev_mid["severity"]),
      prof_sev_heavy["severity"] > prof_sev_mid["severity"])

# hold-out 验证加成（6.12）
prof_h = triage.build_user_profile(PLATES_OK, make_full_runners(26),
                                   hue_norm_result, triage_path="standard",
                                   hold_out={"hit_rate": 0.9})
check("hold-out 通过 → 置信加成 (conf=%.2f)" % prof_h["confidence"],
      prof_h["confidence"] > prof["confidence"])

print("== 5. hue 端到端（severity=0 恒等模拟正常用户）==")
rgbs, hues, _ = hue_test.make_hue_sequence(n=15)
order_norm = hue_test.simulate_arrangement(rgbs, "deutan", 0.0, noise_deg=3.0, rng=31)
jr = hue_test.judge_arrangement(order_norm, rgbs)
check("正常排列 → verdict normal (%s)" % jr["verdict"], jr["verdict"] == "normal")
stage0_fast = triage.triage_stage0(PLATES_OK, {DIM_L: 3, DIM_C: 3, DIM_H: 3})
r = triage.triage_full(stage0_fast, grid_ok, jr)
check("端到端复诊 done", r["level"] == triage.LEVEL_DONE)

# deutan 模拟用户（severity 1.0）→ 轴向应为 red-green（既有结论：deutan 轴 ≈177°）
order_d = hue_test.simulate_arrangement(rgbs, "deutan", 1.0, noise_deg=3.0, rng=31)
jr_d = hue_test.judge_arrangement(order_d, rgbs)
check("deutan 排列 → red-green (%s)" % jr_d["verdict"],
      jr_d["verdict"] == "red-green")
r = triage.triage_full(stage0_deutan, grid_ok, jr_d)
check("deutan 全链路 → done（测试1×测试3 一致）", r["level"] == triage.LEVEL_DONE)

print("\n%d/%d assertions passed" % (PASS, PASS))
print("ALL GREEN")

