# -*- coding: utf-8 -*-
"""
[注意] 已弃用 - 请勿运行 [注意]

此脚本生成 rgb_cleaned.csv（来自原始 "RGB Color Dataset"），
但该数据集 R 通道全部 ∈[0,4]，只有绿/青/蓝色系，缺少红/黄/紫
（美妆核心色系），已确认不可用。

→ 正确数据源为 full_palette.csv（全色域），
  由 ColorBoundless/scripts/generate_full_palette.py 生成。
相关文件 rgb_cleaned.csv / rgb_cleaned_summary.json 已删除。
"""
from __future__ import annotations

import csv
import colorsys
import json
import string
from pathlib import Path

RAW_ROOT = Path(r"e:\作业\欧莱雅比赛项目\download_materials\base_palette\RGB Color Dataset\color\colors")
OUTPUT_CSV = Path(__file__).with_name("rgb_cleaned.csv")
OUTPUT_META = Path(__file__).with_name("rgb_cleaned_summary.json")


def rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert sRGB to CIE Lab using the D65 reference white."""
    def linearize(channel: int) -> float:
        c = channel / 255.0
        if c <= 0.04045:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    r_lin = linearize(r)
    g_lin = linearize(g)
    b_lin = linearize(b)

    x = 0.4124564 * r_lin + 0.3575761 * g_lin + 0.1804375 * b_lin
    y = 0.2126729 * r_lin + 0.7151522 * g_lin + 0.0721750 * b_lin
    z = 0.0193339 * r_lin + 0.1191920 * g_lin + 0.9503041 * b_lin

    x_n = 0.95047
    y_n = 1.0
    z_n = 1.08883

    def lab_f(t: float) -> float:
        if t > 0.008856:
            return t ** (1 / 3)
        return 7.787 * t + 16 / 116

    x_f = lab_f(x / x_n)
    y_f = lab_f(y / y_n)
    z_f = lab_f(z / z_n)

    l = 116 * y_f - 16
    a = 500 * (x_f - y_f)
    b_lab = 200 * (y_f - z_f)
    return l, a, b_lab


def safe_round(value: float, digits: int = 4) -> float:
    return round(float(value), digits)


def main() -> None:
    if not RAW_ROOT.exists():
        raise FileNotFoundError(f"Raw dataset folder not found: {RAW_ROOT}")

    fieldnames = [
        "hex",
        "r",
        "g",
        "b",
        "hue_deg",
        "saturation",
        "value",
        "lightness",
        "lab_l",
        "lab_a",
        "lab_b",
        "source_dir",
    ]

    valid_count = 0
    invalid_count = 0

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for item in sorted(RAW_ROOT.iterdir(), key=lambda p: p.name.lower()):
            if not item.is_dir():
                continue

            folder_name = item.name.lower()
            if len(folder_name) != 6 or any(ch not in string.hexdigits for ch in folder_name):
                invalid_count += 1
                continue

            try:
                r = int(folder_name[0:2], 16)
                g = int(folder_name[2:4], 16)
                b = int(folder_name[4:6], 16)
            except ValueError:
                invalid_count += 1
                continue

            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            hls_h, l, s_hls = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            lab_l, lab_a, lab_b = rgb_to_lab(r, g, b)

            row = {
                "hex": f"#{folder_name.upper()}",
                "r": r,
                "g": g,
                "b": b,
                "hue_deg": safe_round(h * 360),
                "saturation": safe_round(s * 100),
                "value": safe_round(v * 100),
                "lightness": safe_round(l * 100),
                "lab_l": safe_round(lab_l, 4),
                "lab_a": safe_round(lab_a, 4),
                "lab_b": safe_round(lab_b, 4),
                "source_dir": str(item),
            }
            writer.writerow(row)
            valid_count += 1

    summary = {
        "source_root": str(RAW_ROOT),
        "output_csv": str(OUTPUT_CSV),
        "valid_rows": valid_count,
        "invalid_rows": invalid_count,
        "schema": fieldnames,
    }
    OUTPUT_META.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated {OUTPUT_CSV}")
    print(f"Valid rows: {valid_count}")
    print(f"Invalid rows skipped: {invalid_count}")


if __name__ == "__main__":
    main()
