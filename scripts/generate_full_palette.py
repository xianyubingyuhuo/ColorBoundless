# -*- coding: utf-8 -*-
"""
generate_full_palette.py
========================
生成全色域均匀采样色卡（解决原始数据偏色问题）

背景：
    原始 "RGB Color Dataset" 的 296,934 个颜色，R 通道全部 ∈ [0,4]
    → 只有绿/青/蓝色系，几乎没有红/黄/紫（美妆核心色系）！
    → 不能直接作为 base_palette 数据源。

本脚本：
    按固定步长对全色域 (0-255)^3 均匀采样，生成覆盖所有色系的色卡。
    步长 4 → (256/4)^3 = 64^3 = 262,144 种颜色。

输出：
    data/processed/base_palette/full_palette.csv
    字段与 rgb_cleaned.csv 完全一致：
    hex, r, g, b, hue_deg, saturation, value, lightness, lab_l, lab_a, lab_b, source_dir
"""

from __future__ import annotations

import colorsys
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_CSV = PROJECT_ROOT / "data" / "processed" / "base_palette" / "full_palette.csv"

STEP = 4 # 采样步长：0,4,8,...,252 → 每通道 64 个值


def rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """sRGB → CIE Lab（D65 白点）。与 clean_rgb_dataset.py 同一公式。"""
    def linearize(channel: int) -> float:
        c = channel / 255.0
        if c <= 0.04045:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    r_lin, g_lin, b_lin = linearize(r), linearize(g), linearize(b)
    x = 0.4124564 * r_lin + 0.3575761 * g_lin + 0.1804375 * b_lin
    y = 0.2126729 * r_lin + 0.7151522 * g_lin + 0.0721750 * b_lin
    z = 0.0193339 * r_lin + 0.1191920 * g_lin + 0.9503041 * b_lin

    def lab_f(t: float) -> float:
        if t > 0.008856:
            return t ** (1 / 3)
        return 7.787 * t + 16 / 116

    x_f, y_f, z_f = lab_f(x / 0.95047), lab_f(y / 1.0), lab_f(z / 1.08883)
    return (116 * y_f - 16, 500 * (x_f - y_f), 200 * (y_f - z_f))


def main() -> None:
    fieldnames = [
        "hex", "r", "g", "b", "hue_deg", "saturation",
        "value", "lightness", "lab_l", "lab_a", "lab_b", "source_dir",
    ]

    values = list(range(0, 256, STEP)) # [0, 4, 8, ..., 252]
    total = len(values) ** 3 # 64^3 = 262,144
    print(f"采样步长 {STEP} → 每通道 {len(values)} 值 → 共 {total} 色")

    count = 0
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in values:
            for g in values:
                for b in values:
                    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                    _, l, _ = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
                    lab_l, lab_a, lab_b = rgb_to_lab(r, g, b)
                    writer.writerow({
                        "hex": f"#{r:02X}{g:02X}{b:02X}",
                        "r": r, "g": g, "b": b,
                        "hue_deg": round(h * 360, 4),
                        "saturation": round(s * 100, 4),
                        "value": round(v * 100, 4),
                        "lightness": round(l * 100, 4),
                        "lab_l": round(lab_l, 4),
                        "lab_a": round(lab_a, 4),
                        "lab_b": round(lab_b, 4),
                        "source_dir": "generated_full_palette",
                    })
                    count += 1

    print(f"[OK] 生成完成: {OUTPUT_CSV}")
    print(f" 共 {count} 种颜色（全色域均匀采样）")


if __name__ == "__main__":
    main()
