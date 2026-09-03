# -*- coding: utf-8 -*-
"""
⚠️ 已弃用 - 请勿运行 ⚠️

此脚本从原始 "RGB Color Dataset" 的纯色图片提取颜色（rgb_from_images.csv）。
验证结论：图片颜色 = 文件夹名 = R 通道全 ∈[0,4] → 只有绿/青/蓝，
缺少红/黄/紫（美妆核心色系），数据集本身偏色，已确认不可用。

→ 正确数据源为 full_palette.csv（全色域），
  由 scripts/generate_full_palette.py 生成。
相关文件 rgb_from_images.csv 已删除。
"""

"""
extract_palette_from_images.py
==============================
从原始数据集的纯色图片中直接读取 RGB 颜色（不依赖文件夹名）

背景：
    原始 "RGB Color Dataset" 的每个 hex 文件夹里存一张纯色图片
    （256x256 PNG）。本脚本直接读图片像素提取颜色，
    并统计色相分布，判断数据集是否覆盖全色域。

输出：
    data/processed/base_palette/rgb_from_images.csv
    （字段与 rgb_cleaned.csv 一致：hex, r, g, b, hue_deg, saturation,
      value, lightness, lab_l, lab_a, lab_b, source_dir）
"""

from __future__ import annotations

import argparse
import colorsys
import csv
import os
from pathlib import Path

from PIL import Image

# ----------------------------- 路径配置 -----------------------------
RAW_ROOT = Path(r"e:\作业\欧莱雅比赛项目\download_materials\base_palette\RGB Color Dataset\color\colors")
OUTPUT_DIR = Path(r"e:\作业\欧莱雅比赛项目\项目3\ColorBoundless\data\processed\base_palette\parts")
FINAL_CSV = Path(r"e:\作业\欧莱雅比赛项目\项目3\ColorBoundless\data\processed\base_palette\rgb_from_images.csv")

DEFAULT_BATCH_SIZE = 10_000  # 每批处理 1 万个颜色（用户指定）

FIELDNAMES = [
    "hex", "r", "g", "b", "hue_deg", "saturation",
    "value", "lightness", "lab_l", "lab_a", "lab_b", "source_dir",
]


def rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """sRGB → CIE Lab（D65 白点）。"""
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


def classify_hue_group(hue: float, sat: float, val: float) -> str:
    """HSV → 色相族（用于统计分布）"""
    if val < 10:
        return "black"
    if sat < 8:
        return "white" if val > 92 else "gray"
    if hue < 15 or hue >= 345:
        return "red"
    if hue < 45:
        return "orange"
    if hue < 70:
        return "yellow"
    if hue < 160:
        return "green"
    if hue < 195:
        return "cyan"
    if hue < 260:
        return "blue"
    if hue < 290:
        return "purple"
    return "magenta"


def read_pure_color(img_path: Path) -> tuple[int, int, int]:
    """读取纯色图片的中心像素作为该色值。
    图片是 256x256 的纯色 PNG（已验证 = 文件夹名对应的纯色），
    直接读中心像素比 resize 快很多。
    """
    with Image.open(img_path) as im:
        w, h = im.size
        pixel = im.convert("RGB").getpixel((w // 2, h // 2))
    return int(pixel[0]), int(pixel[1]), int(pixel[2])


def process_batch(folders: list[str], start: int, end: int,
                  batch_size: int) -> None:
    """处理第 start 批到第 end-1 批（每批 batch_size 个）。支持断点续传。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    total_batches = (len(folders) + batch_size - 1) // batch_size
    end = min(end, total_batches)

    print(f"共 {len(folders)} 个文件夹 → {total_batches} 批（每批 {batch_size}）")
    print(f"本次处理批次: {start} ~ {end - 1}")

    for batch_idx in range(start, end):
        part_file = OUTPUT_DIR / f"rgb_from_images_part_{batch_idx:03d}.csv"
        if part_file.exists():
            print(f"[批 {batch_idx}/{total_batches}] 已存在，跳过（断点续传）")
            continue

        lo = batch_idx * batch_size
        hi = min(lo + batch_size, len(folders))
        batch_folders = folders[lo:hi]

        count = 0
        with part_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            for folder in batch_folders:
                img_files = list((RAW_ROOT / folder).glob("*_image.png"))
                if not img_files:
                    continue
                r, g, b = read_pure_color(img_files[0])
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
                    "source_dir": str(RAW_ROOT / folder),
                })
                count += 1
        print(f"[批 {batch_idx}/{total_batches}] 完成: {count} 个 → {part_file.name}")


def merge_parts() -> None:
    """合并所有 part 文件成最终 CSV，并删除 part 文件。"""
    part_files = sorted(OUTPUT_DIR.glob("rgb_from_images_part_*.csv"))
    if not part_files:
        print("没有 part 文件可合并")
        return

    total = 0
    with FINAL_CSV.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDNAMES)
        writer.writeheader()
        for pf in part_files:
            with pf.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    writer.writerow(row)
                    total += 1
            pf.unlink()  # 合并后删除 part

    print(f"✅ 合并完成: {total} 个颜色 → {FINAL_CSV}")


def main() -> None:
    parser = argparse.ArgumentParser(description="从纯色图片批量提取颜色")
    parser.add_argument("--start", type=int, default=0, help="起始批次（默认 0）")
    parser.add_argument("--end", type=int, default=10_000, help="结束批次（不含）")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help=f"每批数量（默认 {DEFAULT_BATCH_SIZE}）")
    parser.add_argument("--merge", action="store_true",
                        help="只合并已有 part 文件，不处理图片")
    args = parser.parse_args()

    if args.merge:
        merge_parts()
        return

    if not RAW_ROOT.exists():
        raise FileNotFoundError(f"原始数据目录不存在: {RAW_ROOT}")

    folders = [d for d in sorted(os.listdir(RAW_ROOT))
               if os.path.isdir(RAW_ROOT / d)]

    process_batch(folders, args.start, args.end, args.batch_size)


if __name__ == "__main__":
    main()
