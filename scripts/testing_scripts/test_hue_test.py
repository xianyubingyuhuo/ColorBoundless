# -*- coding: utf-8 -*-
"""验证 hue_test（测试3 色相排列）：序列生成 / 模拟排列 / 错误轴分型 / 落盘

验证策略：
  [1] 渐变序列：色相均匀、全部 sRGB 色域内、确定可复现
  [2] 正常用户（severity=0 + 噪声）：错误分个位数 → verdict=normal
  [3] 完美排列：错误分=0（评分函数基准）
  [4] 缺陷模拟：deutan/protan → red-green 轴；tritan → blue-yellow 轴
  [5] severity 梯度：轻度错误 < 重度错误
  [6] 对比图落盘 results/cvd_test/（上=正确顺序，下=用户排列）
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cvd_test import hue_test

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
print("[1] 渐变序列生成")
print("=" * 62)

N = 15
rgbs, hues, c_used = hue_test.make_hue_sequence(n=N, L=62.0, C=28.0)

# 1a. 色相间隔均匀（全环 360/15 = 24°）
gaps = np.diff(np.concatenate([hues, [hues[0] + 360]]))
check("色相间隔均匀(24°)", np.allclose(gaps, 360.0 / N),
      f"gap ∈ [{gaps.min():.1f}, {gaps.max():.1f}]")

# 1b. 全部色块在 sRGB 色域内（含越界自动压彩度的块）
from cvd_test.hue_test import _lab_in_gamut
labs = []
for rgb in rgbs:
    from cvd_test.color_diff import srgb2lab
    labs.append(srgb2lab(rgb.astype(float)))
# 复查用实际彩度反推：直接检查生成时采用的 c_used 全部合法
check("全部色块色域内", all(
    _lab_in_gamut([62.0, c * np.cos(np.radians(h)), c * np.sin(np.radians(h))])
    for h, c in zip(hues, c_used)),
    f"压彩度块数={int((c_used < 28.0 - 1e-9).sum())}/{N}")

# 1c. 确定性：两次生成完全一致
rgbs2, hues2, _ = hue_test.make_hue_sequence(n=N, L=62.0, C=28.0)
check("生成确定可复现", np.array_equal(rgbs, rgbs2) and np.array_equal(hues, hues2))

# 1d. 出题打乱：0 号块固定第一（UI 参考锚）
disp = hue_test.shuffle_order(N, seed=7)
check("打乱后0号固定第一", disp[0] == 0 and sorted(disp.tolist()) == list(range(N)))

print("=" * 62)
print("[2] 正常用户 / 完美排列 基准")
print("=" * 62)

# 2a. 完美排列：错误分必须为 0
check("完美排列错误分=0", hue_test.arrangement_error(np.arange(N)) == 0)

# 2b. 正常用户（severity=0 + 3° 手抖）：错误分个位数
order_norm = hue_test.simulate_arrangement(rgbs, "deutan", 0.0, noise_deg=3.0, rng=11)
err_norm = hue_test.arrangement_error(order_norm)
check("正常用户错误分个位数", err_norm < 8, f"err={err_norm}")
card_norm = hue_test.judge_arrangement(order_norm, rgbs)
check("正常用户判定=normal", card_norm["verdict"] == "normal",
      f"verdict={card_norm['verdict']}")

print("=" * 62)
print("[3] 缺陷模拟：错误轴分型（与测试1 构成双证据链）")
print("=" * 62)

cards = {}
for kind in ("deutan", "protan", "tritan"):
    order = hue_test.simulate_arrangement(rgbs, kind, 1.0, noise_deg=3.0, rng=23)
    card = hue_test.judge_arrangement(order, rgbs)
    cards[kind] = (order, card)
    expect = "blue-yellow" if kind == "tritan" else "red-green"
    # deutan/protan 零空间精确 → 坍缩重、错误大；tritan 是 Machado 近似投影
    # （最小奇异值 0.156），坍缩弱、错误中等——阈值相应放宽
    err_min = 5 if kind == "tritan" else 25
    check(f"{kind}(sev=1) 错误分>正常量级", card["total_error"] > err_min,
          f"err={card['total_error']}")
    check(f"{kind}(sev=1) 判定={expect}", card["verdict"] == expect,
          f"verdict={card['verdict']} axis={card['axis_deg']}° "
          f"strength={card['axis_strength']}")

# deutan 与 tritan 的错误轴应显著不同（双证据链交叉的数学前提）
ax_d = cards["deutan"][1]["axis_deg"]
ax_t = cards["tritan"][1]["axis_deg"]
axis_gap = abs((ax_d - ax_t + 90) % 180 - 90)   # 环形轴间距 ∈ [0,90]
check("deutan/tritan 错误轴显著不同", axis_gap > 30.0,
      f"deutan={ax_d}° vs tritan={ax_t}° (轴距{axis_gap:.1f}°)")

print("=" * 62)
print("[4] severity 梯度（程度量化）")
print("=" * 62)

err_by_sev = {}
for sev in (0.3, 0.6, 1.0):
    order = hue_test.simulate_arrangement(rgbs, "deutan", sev, noise_deg=3.0, rng=42)
    err_by_sev[sev] = hue_test.arrangement_error(order)
# 轻度 deutan 在 FM100 上本就可能几乎无错（色相序保留），模型同此——
# 断言用非退化链：整体随 severity 上升，且重度显著大于轻度
check("错误分随 severity 非降",
      err_by_sev[0.3] <= err_by_sev[0.6] <= err_by_sev[1.0],
      f"0.3→{err_by_sev[0.3]} / 0.6→{err_by_sev[0.6]} / 1.0→{err_by_sev[1.0]}")
check("重度显著大于轻度", err_by_sev[1.0] - err_by_sev[0.3] > 15,
      f"差={err_by_sev[1.0] - err_by_sev[0.3]}")

print("=" * 62)
print("[5] 对比图落盘（上=正确顺序，下=用户排列）")
print("=" * 62)

out_dir = Path(__file__).resolve().parents[2] / "results" / "cvd_test"
out_dir.mkdir(parents=True, exist_ok=True)

from cvd_test.grid_test import save_grid
save_grid(hue_test.save_strip(rgbs, np.arange(N), None), str(out_dir / "hue_correct_order.jpg"))
for kind, (order, _) in cards.items():
    hue_test.save_compare(rgbs, order, str(out_dir / f"hue_{kind}_arrangement.jpg"))
check("对比图落盘", (out_dir / "hue_deutan_arrangement.jpg").exists(),
      str(out_dir / "hue_*_arrangement.jpg"))

print("=" * 62)
print(f"结果：{PASS} 通过 / {FAIL} 失败")
print("=" * 62)
sys.exit(1 if FAIL else 0)
