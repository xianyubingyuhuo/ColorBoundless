# -*- coding: utf-8 -*-
"""selftest：色觉测评模块自检——一条命令验证整条 CVD 链（测试1/2/3 + 分诊 + 规则库闭环）

跑法（项目根下）：python -m cvd_test.selftest
全绿打印 ALL PASS 并退出码 0；任一失败打印明细并退出码 1。

覆盖面（每条都对应一个可辩护的科学断言）：
    color_diff   sRGB→Lab 标准锚点 + CIEDE2000 Sharma 官方测试对 #1
    cvd_matrix   灰轴不动（行和=1）/ severity=0 恒等 / 混淆对"正常可辨+模拟隐身"
                 / protan 红色明度塌陷（rules cvd_04 的临床事实）
    rules.json   avoid_pairs 模拟后 ΔE 收缩（趋同）+ safe_pairs 保持可辨——
                 "模拟器 × 规则库"联测：规则里的色对确实按所述缺陷表现
    ishihara     正常可见（region_contrast 大）→ deutan 模拟后数字隐身（对比度坍缩）
    grid_test    阶梯法 + simulate_user（虚拟用户）收敛出阈值 + build_profile 三键
    hue_test     deutan 模拟用户排列 → verdict=red-green；正常用户 → normal
    triage       快筛三分支（fast/standard/deep）+ build_user_profile 类型投票
"""
import json
import sys
from pathlib import Path

import numpy as np

from . import grid_test, hue_test, ishihara, triage
from .color_diff import ciede2000, srgb2lab
from .cvd_matrix import confusion_pair, simulate_cvd

RULES = Path(__file__).resolve().parents[1] / "data" / "knowledge_base" / "cvd_rules" / "rules.json"

_RES = []


def check(name, cond, detail=""):
    _RES.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name + (("   | " + detail) if detail else ""))


def _h2rgb(h):
    """"#RRGGBB" → uint8 rgb（rules.json 里的色对是 hex 字符串）"""
    h = str(h).strip().lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.uint8)


def dE_pair(rgb_a, rgb_b, kind=None, severity=1.0):
    """色对 ΔE00；kind 给定则在模拟视角下计算（模拟后趋同 → ΔE 变小）"""
    a = _h2rgb(rgb_a) if isinstance(rgb_a, str) else np.asarray(rgb_a, dtype=np.uint8)
    b = _h2rgb(rgb_b) if isinstance(rgb_b, str) else np.asarray(rgb_b, dtype=np.uint8)
    if kind is None:
        return float(ciede2000(srgb2lab(a.astype(float)), srgb2lab(b.astype(float))))
    sa = simulate_cvd(a, kind, severity).astype(float)
    sb = simulate_cvd(b, kind, severity).astype(float)
    return float(ciede2000(srgb2lab(sa), srgb2lab(sb)))


# ---- 1. color_diff：标准锚点（错一格，全项目颜色计算的地基就歪） ----
lab = srgb2lab(np.array([255.0, 0.0, 0.0]))
check("color_diff srgb2lab 红=(53.24,80.09,67.20)",
      bool(np.allclose(lab, [53.24, 80.09, 67.20], atol=0.15)), str(lab.round(2).tolist()))
d00 = float(ciede2000([50.0, 2.6772, -79.7751], [50.0, 0.0, -82.7485]))
check("color_diff CIEDE2000=Sharma#1(2.0425)", abs(d00 - 2.0425) < 0.01, f"got {d00:.4f}")

# ---- 2. cvd_matrix：模拟器的数学性质 ----
gray = np.array([200, 200, 200], dtype=np.uint8)
ok_gray = all((simulate_cvd(gray, k, 1.0) == gray).all()
              for k in ("protan", "deutan", "tritan"))
check("cvd_matrix 灰轴不动(三型)", ok_gray)
_red = np.array([220, 20, 60], dtype=np.uint8)
check("cvd_matrix severity=0 恒等",
      (simulate_cvd(_red, "deutan", 0.0) == _red).all())
_rgb_a, _rgb_b, dE_n, dE_s = confusion_pair(np.array([180.0, 120.0, 90.0]), "deutan", 1.0)
check("cvd_matrix 混淆对 正常可辨+模拟隐身",
      dE_n >= 12.0 and dE_s < 1.5, f"dE_normal={dE_n:.1f} dE_sim={dE_s:.2f}")
L0 = float(srgb2lab(np.asarray(_red, float))[0])
L1 = float(srgb2lab(simulate_cvd(_red, "protan", 1.0).astype(float))[0])
check("cvd_matrix protan 红色明度塌陷(cvd_04)", L1 < L0 - 3.0, f"L {L0:.1f} -> {L1:.1f}")

# ---- 3. rules.json × 模拟器联测（规则所述行为必须真实发生） ----
rules = {r["rule_id"]: r for r in json.loads(RULES.read_text(encoding="utf-8"))}
for rid, kind in (("cvd_01", "deutan"), ("cvd_02", "tritan"), ("cvd_04", "protan")):
    rule = rules[rid]
    shrink = [dE_pair(a, b, kind) for a, b in rule["avoid_pairs"]]
    keep = [dE_pair(a, b, kind) for a, b in rule["safe_pairs"]]
    check(f"{rid} {kind} avoid_pairs 模拟后趋同", all(
        s < dE_pair(a, b) / 3.0 for s, (a, b) in zip(shrink, rule["avoid_pairs"])),
        "sim=" + ",".join(f"{s:.1f}" for s in shrink))
    check(f"{rid} {kind} safe_pairs 保持可辨(ΔE>5)", all(s > 5.0 for s in keep),
          "sim=" + ",".join(f"{s:.1f}" for s in keep))
lum = lambda h: sum(w * int(h[i:i + 2], 16) / 255.0 for w, i in
                    zip((0.2126, 0.7152, 0.0722), (1, 3, 5)))
_gray_pairs = rules["cvd_01"]["safe_pairs"] + rules["cvd_04"]["safe_pairs"]
check("cvd_03 灰阶亮度差>=0.18(规则样例对)",
      all(abs(lum(a) - lum(b)) >= 0.18 for a, b in _gray_pairs[:2]))

# ---- 4. 测试1 伪等色图：正常人看得见，deutan 模拟者看不见 ----
img, info = ishihara.make_plate("8", "deutan", 1.0, seed=8)
mask = ishihara._digit_mask("8", img.shape[0])
c_normal = ishihara.region_contrast(img, mask)
c_sim = ishihara.region_contrast(ishihara.simulate_plate(img, "deutan", 1.0), mask)
check("ishihara 正常视觉可见(对比度>8)", c_normal > 8.0, f"{c_normal:.1f}")
check("ishihara deutan 数字隐身(对比度<2.5)", c_sim < 2.5, f"{c_sim:.1f}")
check("ishihara 判定器", ishihara.judge_answer(" 8 ", info)
      and not ishihara.judge_answer("3", info))

# ---- 5. 测试2 网格阶梯：虚拟用户跑完必须收敛出三维阈值 ----
runners = {}
for i, (dim, jnd) in enumerate(((grid_test.DIM_L, 4.0), (grid_test.DIM_C, 5.0),
                                (grid_test.DIM_H, 7.0))):
    r = grid_test.ThresholdRunner(dim, start_level=0, n_reversals=3,
                                  max_rounds=12, seed=11 + i)
    grid_test.simulate_user(r, true_delta=jnd, p_correct=0.95)
    runners[dim] = r
thr = {d: r.threshold() for d, r in runners.items()}
check("grid_test 三维阶梯收敛", all(r.done for r in runners.values())
      and all(v is not None and 1.0 <= v <= 12.0 for v in thr.values()),
      " ".join(f"{d}={v:.2f}" for d, v in thr.items()))
prof = grid_test.build_profile(runners)
check("grid_test build_profile 三键齐全",
      all(prof[k] is not None for k in ("dL_threshold", "dC_threshold", "dH_threshold")))

# ---- 6. 测试3 色相排列：deutan 模拟者判 red-green，正常用户 normal ----
rgbs, hues, _ = hue_test.make_hue_sequence(n=15)
sim_lab = srgb2lab(simulate_cvd(rgbs.astype(float), "deutan", 1.0).astype(float))
seen_h = np.degrees(np.arctan2(sim_lab[:, 2], sim_lab[:, 1])) % 360.0


def _arrange(h):
    rel = (h - h[0]) % 360.0
    return [0] + (np.argsort(rel[1:]) + 1).tolist()


hj_deutan = hue_test.judge_arrangement(_arrange(seen_h), rgbs)
hj_normal = hue_test.judge_arrangement(_arrange(hues), rgbs)
check("hue_test deutan 排列→red-green", hj_deutan["verdict"] == "red-green",
      f"axis={hj_deutan['axis_deg']} err={hj_deutan['total_error']:.1f}")
check("hue_test 正常排列→normal", hj_normal["verdict"] == "normal",
      f"err={hj_normal['total_error']:.1f}")

# ---- 7. 分诊状态机：快筛三分支 + 档案投票 ----
_dims = (grid_test.DIM_L, grid_test.DIM_C, grid_test.DIM_H)
_good = {d: 6 for d in _dims}
_mid = {d: 3 for d in _dims}
_bad = {d: 1 for d in _dims}
_ok_plates = [{"kind": "deutan", "correct": True}, {"kind": "protan", "correct": True}]
_bad_plates = [{"kind": "deutan", "correct": False}, {"kind": "protan", "correct": False}]
t_fast = triage.triage_stage0(_ok_plates, _good)
t_mid = triage.triage_stage0([_ok_plates[0], {"kind": "protan", "correct": False}], _mid)
t_deep = triage.triage_stage0(_bad_plates, _bad, subjective=True)
check("triage 快筛三分支 fast/standard/deep",
      t_fast["level"] == "fast" and t_mid["level"] == "standard"
      and t_deep["level"] == "deep",
      f"{t_fast['level']}/{t_mid['level']}/{t_deep['level']}")
profile = triage.build_user_profile(_bad_plates, runners, hj_deutan, "deep")
check("triage 档案投票 deutan+置信封顶",
      profile["cvd_type"] == "deutan" and profile["confidence"] <= 0.95,
      f"type={profile['cvd_type']} conf={profile['confidence']}")

# ---- 汇总 ----
n_ok = sum(1 for _, ok in _RES if ok)
print(f"\n{'ALL PASS' if n_ok == len(_RES) else 'HAS FAIL'}: {n_ok}/{len(_RES)}")
sys.exit(0 if n_ok == len(_RES) else 1)

