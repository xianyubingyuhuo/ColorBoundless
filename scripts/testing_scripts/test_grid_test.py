# -*- coding: utf-8 -*-
"""验证 cvd_test 模块：color_diff 精度 + grid_test 算法正确性 + 阶梯法收敛性

验证策略（三层，全自动断言）：
  [1] color_diff：sRGB↔Lab 往返一致性、标准色 Lab 值、CIEDE2000 官方测试对
  [2] make_round：异色块唯一性（ΔE 最大块=标注位）、三维度严格分离、样例图落盘
  [3] 阶梯法：模拟三类用户（Normal/普通/CVD），验证阈值收敛到真值邻域
"""
import sys
from pathlib import Path

import numpy as np

# testing_scripts/ 的上上级 = ColorBoundless 根目录，让它可被 import
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cvd_test import color_diff, grid_test

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name} {detail}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")


print("=" * 62)
print("[1] color_diff 精度验证")
print("=" * 62)

# 1a. sRGB→Lab→sRGB→Lab 往返一致（随机 1000 色，Lab 域比较，容差 0.6 ≈ uint8 量化级）
rng = np.random.default_rng(42)
rgb_rand = rng.integers(0, 256, size=(1000, 3)).astype(np.float64)
lab_ref = color_diff.srgb2lab(rgb_rand)
lab_rt = color_diff.srgb2lab(color_diff.lab2srgb(lab_ref).astype(np.float64))
err = np.abs(lab_rt - lab_ref).max()
check("sRGB→Lab→sRGB→Lab 往返误差", err < 0.6, f"max_err={err:.4f}")

# 1b. 标准色 Lab 值（sRGB 红 (255,0,0) → L*≈53.24, a*≈80.09, b*≈67.20，D65 标准值）
lab_red = color_diff.srgb2lab([255, 0, 0])
check("标准红 Lab 值", np.allclose(lab_red, [53.24, 80.09, 67.20], atol=0.1),
      f"got {lab_red.round(2).tolist()}")

# 1c. CIEDE2000 官方测试对（Sharma et al. 2005 数据集，容差 ±0.01）
pairs = [
    ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
    ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
    ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
    ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2592, 0.3350), 1.0000),
]
for i, (l1, l2, expect) in enumerate(pairs, 1):
    got = float(color_diff.ciede2000(np.array(l1), np.array(l2)))
    check(f"CIEDE2000 官方对#{i}", abs(got - expect) < 0.01,
          f"expect={expect} got={got:.4f}")

# 1d. 相同色 ΔE=0
check("同色 ΔE00=0", float(color_diff.ciede2000([50, 20, 30], [50, 20, 30])) == 0.0)

print("=" * 62)
print("[2] make_round 算法正确性")
print("=" * 62)

# 2a. 三个维度各生成 5 轮：验证显示出来的 odd 格确实是"离 base 最远的格"
#     （基准统一用显示色： RGB 量化噪声 ±0.5，必须两边同源比较，否则假失败）
for dim in (grid_test.DIM_L, grid_test.DIM_C, grid_test.DIM_H):
    ok_all = True
    for trial in range(5):
        # 用各维最易档 delta，保证信号远超量化噪声
        img, info = grid_test.make_round(dim, delta=grid_test.LEVELS[dim][0],
                                         rng=np.random.default_rng(100 + trial))
        n, cell, gap = info["n"], 90, 6
        odd_pos = tuple(info["odd_pos"])

        def cell_lab(pos):
            """取某格中心像素的显示 Lab"""
            y, x = gap + pos[0] * (cell + gap), gap + pos[1] * (cell + gap)
            return color_diff.srgb2lab(img[y + cell // 2, x + cell // 2].astype(np.float64))

        # base 基准格：任取一个非 odd 的格（所有 base 格显示同一 RGB）
        base_pos = (0, 0) if odd_pos != (0, 0) else (0, 1)
        base_ref = cell_lab(base_pos)

        de_odd = float(color_diff.ciede2000(base_ref, cell_lab(odd_pos)))
        worst_other = 0.0
        for r in range(n):
            for c in range(n):
                if (r, c) in (odd_pos, base_pos):
                    continue
                worst_other = max(worst_other,
                                  float(color_diff.ciede2000(base_ref, cell_lab((r, c)))))
        if de_odd <= worst_other:   # odd 必须严格最远（base 副本只有量化噪声 ~0.5）
            ok_all = False
    check(f"异色块唯一且可检出 ({dim})", ok_all, "5轮×3维 显示域 odd ΔE 严格最大")

# 2b. 三维度严格分离：ΔL 轮 a/b 不变；ΔC 轮 L 不变；ΔH 轮 L、C 不变
sep_ok = True
for dim in (grid_test.DIM_L, grid_test.DIM_C, grid_test.DIM_H):
    _, info = grid_test.make_round(dim, delta=6.0, rng=np.random.default_rng(7))
    b1, b2 = np.array(info["base_lab"]), np.array(info["odd_lab"])
    dL = abs(b2[0] - b1[0])
    dC = abs(np.hypot(b2[1], b2[2]) - np.hypot(b1[1], b1[2]))
    h1 = np.degrees(np.arctan2(b1[2], b1[1]))
    h2 = np.degrees(np.arctan2(b2[2], b2[1]))
    dH = abs((h2 - h1 + 180) % 360 - 180)
    # 每个维度只允许自己的通道变化，其余两个通道泄漏应 < 0.5（数值舍入容差）
    leaks = {grid_test.DIM_L: (dC, dH), grid_test.DIM_C: (dL, dH), grid_test.DIM_H: (dL, dC)}
    if any(v > 0.5 for v in leaks[dim]):
        sep_ok = False
        print(f"    维度泄漏 {dim}: dL={dL:.2f} dC={dC:.2f} dH={dH:.2f}")
check("三维度严格分离（无交叉污染）", sep_ok)

# 2c. 样例图落盘（供人工目检：明显档 vs 最难档）
out_dir = Path(__file__).resolve().parents[2] / "results" / "cvd_test"
out_dir.mkdir(parents=True, exist_ok=True)
info_hard = None
for dim in (grid_test.DIM_L, grid_test.DIM_C, grid_test.DIM_H):
    img_easy, _ = grid_test.make_round(dim, delta=grid_test.LEVELS[dim][0],
                                       rng=np.random.default_rng(1))
    img_hard, info_hard = grid_test.make_round(dim, delta=grid_test.LEVELS[dim][-1],
                                               rng=np.random.default_rng(2))
    grid_test.save_grid(img_easy, str(out_dir / f"grid_{dim}_easy.jpg"))
    grid_test.save_grid(img_hard, str(out_dir / f"grid_{dim}_hard.jpg"))
check("样例图落盘", (out_dir / "grid_L_easy.jpg").exists(),
      str(out_dir) + f"（最难档 odd={info_hard['odd_pos']}，人工核对用）")

print("=" * 62)
print("[3] 阶梯法收敛性（模拟用户）")
print("=" * 62)

# 3a. 三类虚拟用户 × 三维度：真值取 LEVELS 第 3/5 级与"完美用户"
scenarios = [
    ("普通用户(真值=第3级)", 2),   # LEVELS index 2
    ("敏锐用户(真值=第5级)", 4),   # index 4
    ("完美用户(全量程)", 99),      # 永远看得见 → 跑到最细级
]
for label, lv in scenarios:
    for dim in (grid_test.DIM_L, grid_test.DIM_C, grid_test.DIM_H):
        runner = grid_test.ThresholdRunner(dim, seed=2024)
        levels = grid_test.LEVELS[dim]
        true_delta = levels[lv] if lv < len(levels) else 0.5
        grid_test.simulate_user(runner, true_delta=true_delta, p_correct=0.9)
        est = runner.threshold()
        if lv == 99:
            ok = est <= levels[-1] * 1.5               # 完美用户收敛在量程底部
        else:
            # 收敛区间：下界 = 更难级×0.8，上界 = 更易级×1.2
            # （1-up/1-down 稳态在 50% 可见点 ≈ JND，会落在真值相邻级之间）
            lo = levels[min(lv + 1, len(levels) - 1)] * 0.8
            hi = levels[max(lv - 1, 0)] * 1.2
            ok = lo <= est <= hi
        check(f"{label} · {dim}维", ok,
              f"true={true_delta} est={est:.2f} rounds={len(runner.history)}")

# 3b. 完整档案构建
runners = {d: grid_test.ThresholdRunner(d, seed=7)
           for d in (grid_test.DIM_L, grid_test.DIM_C, grid_test.DIM_H)}
for d, r in runners.items():
    grid_test.simulate_user(r, true_delta=grid_test.LEVELS[d][3], p_correct=0.9)
profile = grid_test.build_profile(runners)
check("UserColorProfile 构建", all(v is not None for v in profile.values()),
      str({k: round(v, 2) for k, v in profile.items()}))

print("=" * 62)
print(f"结果：{PASS} 通过 / {FAIL} 失败")
print("=" * 62)
sys.exit(1 if FAIL else 0)
