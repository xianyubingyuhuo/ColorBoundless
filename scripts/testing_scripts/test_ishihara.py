# -*- coding: utf-8 -*-
"""验证 cvd_matrix + ishihara：CVD 模拟性质 / 混淆对数学 / 伪等色图可见性

验证策略（四层）：
  [1] cvd_matrix：severity=0 恒等、灰轴不变（明度保留）、零空间存在性
  [2] 混淆对：模拟域不可分（dE_sim 小）+ 正常域可分（dE_normal 大）+ 类型方向不同
  [3] 伪等色图：正常视觉可辨数字、对应缺陷模拟后数字隐身、落盘样例图
  [4] judge_answer 判定逻辑
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cvd_test import color_diff, cvd_matrix, ishihara

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
print("[1] cvd_matrix 模拟性质")
print("=" * 62)

# 1a. severity=0 → 恒等（随机 500 色，模拟前后 ΔE 全为 0）
rng = np.random.default_rng(42)
rgb_rand = rng.integers(0, 256, size=(500, 3)).astype(np.float64)
for kind in cvd_matrix._CVD_KINDS:
    dE = color_diff.ciede2000(color_diff.srgb2lab(rgb_rand),
                              color_diff.srgb2lab(cvd_matrix.simulate_cvd(rgb_rand, kind, 0.0).astype(float)))
    check(f"severity=0 恒等 ({kind})", float(np.max(dE)) == 0.0)

# 1b. 灰轴不变：色盲保留明度感知 → (v,v,v) 模拟后必须仍是 (v',v',v') 且 v'≈v
grays = rng.uniform(20, 235, size=(50, 1)) * np.ones((1, 3))
ok_gray, ok_white = True, True
for kind in cvd_matrix._CVD_KINDS:
    sim = cvd_matrix.simulate_cvd(grays, kind, 1.0).astype(float)
    if np.abs(sim - sim[:, :1]).max() > 0.5:      # 模拟后 RGB 三通道应仍相等
        ok_gray = False
    w = cvd_matrix.simulate_cvd([[255, 255, 255]], kind, 1.0).astype(float)
    if np.abs(w - 255).max() > 1.0:               # 白点不变（行和=1 的直接推论）
        ok_white = False
check("灰轴不动（明度感知保留）", ok_gray)
check("白点不变", ok_white)

# 1c. 零空间存在性：deutan/protan 矩阵（Machado）为精确投影，最小奇异值≈0；
#     tritan 矩阵原文即"最小二乘近似投影"，方向近似（tritan 占比 <1%，标注局限）
for kind in cvd_matrix._CVD_KINDS:
    s = np.linalg.svd(cvd_matrix._M_FULL[kind], compute_uv=False)
    thresh = 0.01 if kind in ("deutan", "protan") else 0.2
    tag = "精确零空间" if thresh < 0.05 else "近似方向（Machado 原文即近似投影）"
    check(f"混淆方向有效 ({kind})", s[-1] < thresh,
          f"min_singular={s[-1]:.4f} [{tag}]")

print("=" * 62)
print("[2] 混淆色对（伪等色图的原材料）")
print("=" * 62)

base = color_diff.lab2srgb([60.0, 25.0, 20.0]).astype(np.float64)
for kind in ("deutan", "protan"):
    rgb_a, rgb_b, dE_n, dE_s = cvd_matrix.confusion_pair(base, kind, 1.0, step=0.12)
    # 职责①等色性（数学性质）：dE_sim 仅剩 uint8 量化残差
    check(f"混淆对模拟域不可分 ({kind})", dE_s < 1.5, f"dE_sim={dE_s:.3f}")
    # 职责②可分性由【自适应步长】实现（make_plate 负责）——此处验证其单调有效性：
    # 线性域 step 加倍 → 正常域 ΔE 显著上升（自适应循环"加大步长"才有意义）
    _, _, dE_small, _ = cvd_matrix.confusion_pair(base, kind, 1.0, step=0.05)
    _, _, dE_big, _ = cvd_matrix.confusion_pair(base, kind, 1.0, step=0.25)
    check(f"正常域差异随步长单调增长 ({kind})", dE_big > dE_small * 2.5,
          f"step0.05→{dE_small:.2f} / step0.25→{dE_big:.2f}")

# deutan 与 protan 的混淆方向应显著不同（否则无法分型出题）
d_deu = cvd_matrix.confusion_direction("deutan")
d_pro = cvd_matrix.confusion_direction("protan")
cos = abs(float(d_deu @ d_pro) / (np.linalg.norm(d_deu) * np.linalg.norm(d_pro)))
check("deutan/protan 混淆方向不同", cos < 0.99, f"|cos|={cos:.4f}")

print("=" * 62)
print("[3] 伪等色图（测试1 主体）")
print("=" * 62)

out_dir = Path(__file__).resolve().parents[2] / "results" / "cvd_test"
out_dir.mkdir(parents=True, exist_ok=True)

for kind in ("deutan", "protan"):
    img, info = ishihara.make_plate(8, kind=kind, severity=1.0, seed=2024)
    mask = ishihara._digit_mask(8, img.shape[0])

    # 3a. 正常视觉：数字区 vs 背景区 ΔE 足够大 → 正常人看得见数字
    dE_vis = ishihara.region_contrast(img, mask)
    check(f"正常视觉可辨 ({kind})", dE_vis > 6.0, f"ΔE={dE_vis:.2f}")

    # 3b. 对应缺陷模拟后：ΔE 塌缩 → 数字隐身（= 该类用户看不到）
    sim_img = ishihara.simulate_plate(img, kind, 1.0)
    dE_blind = ishihara.region_contrast(sim_img.astype(float), mask)
    check(f"对应缺陷下数字隐身 ({kind})", dE_blind < 3.0, f"ΔE={dE_blind:.2f}")

    # 3c. 落盘：原图 + 模拟图（人工目检：模拟图上应完全看不出 8）
    grid_test_save = out_dir / f"plate_{kind}_8.jpg"
    from cvd_test.grid_test import save_grid
    save_grid(img, str(grid_test_save))
    save_grid(sim_img, str(out_dir / f"plate_{kind}_8_simulated.jpg"))
    check(f"样例图落盘 ({kind})", grid_test_save.exists(), str(grid_test_save))

# 3d. severity<1：轻度用户数字"隐身不完全"（残差随 severity 上升）
img_full, _ = ishihara.make_plate(8, kind="deutan", severity=1.0, seed=2024)
img_mild, _ = ishihara.make_plate(8, kind="deutan", severity=0.5, seed=2024)
mask8 = ishihara._digit_mask(8, img_full.shape[0])
blind_full = ishihara.region_contrast(ishihara.simulate_plate(img_full, "deutan", 1.0).astype(float), mask8)
blind_mild = ishihara.region_contrast(ishihara.simulate_plate(img_mild, "deutan", 0.5).astype(float), mask8)
check("轻度(severity=0.5)残留可见度更高", blind_mild > blind_full * 2,
      f"mild={blind_mild:.2f} vs full={blind_full:.2f}")

print("=" * 62)
print("[4] judge_answer 判定")
print("=" * 62)
info = {"digit": "8"}
check("答对 → 正常", ishihara.judge_answer("8", info) is True)
check("带空格答对", ishihara.judge_answer(" 8 ", info) is True)
check("答错 → 缺陷嫌疑", ishihara.judge_answer("3", info) is False)
check("看不清 → 缺陷嫌疑", ishihara.judge_answer("", info) is False)

print("=" * 62)
print(f"结果：{PASS} 通过 / {FAIL} 失败")
print("=" * 62)
sys.exit(1 if FAIL else 0)
