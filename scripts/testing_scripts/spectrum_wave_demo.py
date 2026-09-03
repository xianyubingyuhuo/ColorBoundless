# -*- coding: utf-8 -*-
"""spectrum_wave_demo：光谱波浪图可视化 + CVD 模拟对比（project.md 6.14 演示素材）

链路：波长 nm → CMF(Wyman 2013 解析近似) → XYZ → Lab(D65)
      → sRGB 色域内压彩度（复用 hue_test 二分法）→ 波浪渲染 → simulate_cvd
产出：normal / deutan / protan 三视角对比图 → results/cvd_test/

说明：单色光谱色大多在 sRGB 色域外（尤其 520-540nm 纯绿），压彩度后
      色带偏淡是显示器色域的物理限制，不是 bug——这本身就是答辩素材。
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cvd_test.color_diff import _D65, lab2srgb
from cvd_test.cvd_matrix import simulate_cvd
from cvd_test.grid_test import save_grid
from cvd_test.hue_test import _lab_in_gamut

D65_X100 = _D65 * 100.0     # CMF 按 Y 峰=100 归一后，白点同步放大


def wyman_cmf(wl):
    """CIE 1931 2° CMF 的解析近似（Wyman, Sloan & Shirley 2013, JCGT）

    多 lobes 高斯拟合：x̄ 三叶、ȳ/z̄ 各两叶；分段 σ（λ<μ 用 s1，否则 s2）。
    演示精度足够；正式版换逐点 CMF 表（colour-science 可取）。
    """
    lam = np.asarray(wl, dtype=np.float64)

    def g(mu, s1, s2):
        s = np.where(lam < mu, s1, s2)
        return np.exp(-0.5 * ((lam - mu) / s) ** 2)

    x = (1.056 * g(599.8, 37.9, 31.0) + 0.362 * g(442.0, 16.0, 26.7)
         - 0.065 * g(501.1, 20.4, 26.2))
    y = 0.821 * g(568.8, 46.9, 40.5) + 0.286 * g(530.9, 16.3, 31.1)
    z = 1.217 * g(437.0, 11.8, 36.0) + 0.681 * g(459.0, 26.0, 13.8)
    return x, y, z


# 全谱 ȳ 峰值（≈1.0 @ 555nm）：把光谱**整体**缩放到最亮波长 L*≈95。
# 教训（diag_wave 诊断）：单波长调用时 y.max() 是自己 → L 恒=100；
# 且 L*=100 的灰在浮点上恰触色域边界被 _lab_in_gamut 误判越界 → 二分 k=0 全白。
_Y_PEAK = float(wyman_cmf(np.arange(380.0, 781.0))[1].max())


def spectrum_lab(wl):
    """波长 nm → Lab（整体缩放使最亮波长 L*≈95，D65 白点下计算）

    L*≈95 对应 Y_peak = ((95+16)/116)^3 · 100 ≈ 87.6：
    单色光显示亮度本就低于白场；同时避开 L*=100 的色域边界浮点问题。
    """
    x, y, z = wyman_cmf(wl)
    scale = 87.6 / _Y_PEAK
    xyz = np.stack([x * scale, y * scale, z * scale], axis=-1)
    t = xyz / D65_X100
    f = np.where(t > 216.0 / 24389.0, np.cbrt(t), (24389.0 / 27.0 * t + 16.0) / 116.0)
    L = 116.0 * f[..., 1] - 16.0
    a = 500.0 * (f[..., 0] - f[..., 1])
    b = 200.0 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def gamut_fit(lab):
    """Lab → sRGB 色域内：越界时向无彩轴二分压彩度（保 L* 与色相角）"""
    L, a, b = (float(v) for v in lab)
    if _lab_in_gamut([L, a, b]):
        return lab2srgb([L, a, b]), 1.0
    lo, hi = 0.0, 1.0
    for _ in range(32):
        k = (lo + hi) / 2.0
        if _lab_in_gamut([L, a * k, b * k]):
            lo = k
        else:
            hi = k
    k = lo * 0.995
    return lab2srgb([L, a * k, b * k]), k


def render_wave(wl_lo=380, wl_hi=780, width=1100, height=480,
                amp=70, period=330, dot_r=16):
    """渲染光谱波浪图：正弦曲线沿线上铺光谱色圆点 + 波长刻度"""
    img = np.full((height, width, 3), 250, dtype=np.uint8)
    x0, y0 = 30, height // 2 - 30
    lams = np.arange(wl_lo, wl_hi + 1)
    step = (width - 60) / len(lams)

    colors, ks = [], []
    for wl in lams:
        rgb, k = gamut_fit(spectrum_lab(wl))
        colors.append(rgb)
        ks.append(k)
    colors = np.array(colors)

    for i, wl in enumerate(lams):
        px = int(x0 + i * step)
        py = int(y0 - amp * np.sin(2.0 * np.pi * px / period))
        cv2.circle(img, (px, py), dot_r, colors[i].tolist(), -1, lineType=cv2.LINE_AA)

    for nm in (380, 440, 500, 560, 620, 700, 780):
        px = int(x0 + (nm - wl_lo) * step)
        cv2.line(img, (px, height - 66), (px, height - 34), (140, 140, 140), 1)
        cv2.putText(img, str(nm), (px - 24, height - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (90, 90, 90), 1, cv2.LINE_AA)
    cv2.putText(img, "Visible spectrum wave 380-780nm (Wyman 2013 CMF approx)",
                (20, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (70, 70, 70), 1, cv2.LINE_AA)
    return img, colors, np.array(ks)


def label_row(img, text):
    """图顶加标签条"""
    bar = np.full((34, img.shape[1], 3), 60, dtype=np.uint8)
    cv2.putText(bar, text, (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def main():
    wave, colors, ks = render_wave()

    # sanity check：关键波长压彩度情况（540nm 纯绿必然越界被压）
    print("关键波长 sanity check（RGB / 压彩度系数 k）:")
    for nm in (460, 500, 520, 540, 560, 580, 620, 700):
        i = nm - 380
        print(f"  {nm}nm  RGB={colors[i].tolist()}  k={ks[i]:.3f}")

    rows = [
        label_row(wave, "Normal vision (what most people see)"),
        label_row(simulate_cvd(wave, "deutan", 1.0).astype(np.uint8),
                  "Deutan (green-blind) simulated view"),
        label_row(simulate_cvd(wave, "protan", 1.0).astype(np.uint8),
                  "Protan (red-blind) simulated view"),
    ]
    gap = np.full((14, wave.shape[1], 3), 255, dtype=np.uint8)
    canvas = np.vstack([rows[0], gap, rows[1], gap, rows[2]])

    out_dir = Path(__file__).resolve().parents[2] / "results" / "cvd_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "spectrum_wave_cvd_compare.jpg"
    save_grid(canvas, str(out))
    print(f"\n已落盘: {out}")
    print("观察点: deutan/protan 视角下红绿段塌成土黄灰、蓝黄段保留——")
    print("        这正是波浪图定位测试能看到'指认塌缩区'的原因。")


if __name__ == "__main__":
    main()
