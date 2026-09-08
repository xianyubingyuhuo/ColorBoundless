# -*- coding: utf-8 -*-
"""
process_skin_tone.py
====================
肤色与底妆（skin_tone）数据处理脚本 —— Day 2-3

目标：
    把清洗后的 skin_tone_cleaned.csv（12,102 个产品）处理成
    "可快速过滤的结构化索引"。

架构原则（来自工业级建议）：
    skin_tone 是"产品库" → 结构化过滤为主（undertone/lightness 快速圈定）
    → 不用全量塞进 RAG；仅当需要"语义搜索产品文案"时才用少量 embedding

产出（写入 models/vector_store/skin_tone_index.npz）：
    - brand_array : (N,) 品牌
    - product_array : (N,) 产品名
    - name_array : (N,) 色号名
    - hex_array : (N,) 十六进制颜色
    - rgb_array : (N, 3) RGB
    - lab_array : (N, 3) Lab（用于和肤色做色差匹配）
    - undertone_encoded : (N,) 0=cool, 1=warm, 2=neutral
    - lightness_encoded : (N,) 0=deep, 1=medium, 2=light
    - lookup : dict {(undertone_id, lightness_id): [索引列表]}

为什么这样做？
    1. undertone + lightness 是"肤色→底妆"最关键的快速筛选条件
    2. 查询表让筛选变成 O(1) 字典查找，而不是全表扫描
    3. Lab 特征用于后续和"用户肤色"算 CIEDE2000 色差
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------- 路径配置 -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = PROJECT_ROOT / "data" / "processed" / "skin_tone" / "skin_tone_cleaned.csv"
OUTPUT_NPZ = PROJECT_ROOT / "models" / "vector_store" / "skin_tone_index.npz"
OUTPUT_META = PROJECT_ROOT / "models" / "vector_store" / "skin_tone_meta.json"

# undertone 编码
UNDERTONE_TO_ID = {"cool": 0, "warm": 1, "neutral": 2}
ID_TO_UNDERTONE = {v: k for k, v in UNDERTONE_TO_ID.items()}

# lightness 分档（lightness 字段是 0-1）
LIGHTNESS_BINS = [0.0, 0.35, 0.65, 1.01]
LIGHTNESS_NAMES = ["deep", "medium", "light"]


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


def encode_lightness(lightness: float) -> int:
    """把 0-1 的 lightness 分档：0=deep, 1=medium, 2=light"""
    for i in range(len(LIGHTNESS_BINS) - 1):
        if LIGHTNESS_BINS[i] <= lightness < LIGHTNESS_BINS[i + 1]:
            return i
    return 2 # 兜底


def main() -> None:
    print(f"[1/4] 读取清洗数据: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f" 共 {len(df)} 个产品")

    # ------------------- [2/4] 特征编码 + 计算 Lab -------------------
    print("[2/4] 特征编码 + 计算 Lab...")
    brand_array = df["brand"].astype(str).to_numpy()
    product_array = df["product"].astype(str).to_numpy()
    name_array = df["name"].astype(str).to_numpy()
    hex_array = df["hex"].astype(str).to_numpy()
    rgb_array = df[["r", "g", "b"]].to_numpy(dtype=np.float32)

    # undertone 编码
    undertone_encoded = df["undertone"].map(UNDERTONE_TO_ID).to_numpy(dtype=np.int8)

    # lightness 分档
    lightness_encoded = np.array(
        [encode_lightness(v) for v in df["lightness"].to_numpy()], dtype=np.int8
    )

    # 计算 Lab（用于后续色差匹配）
    lab_list = [rgb_to_lab(int(r), int(g), int(b))
                for r, g, b in df[["r", "g", "b"]].itertuples(index=False)]
    lab_array = np.array(lab_list, dtype=np.float32)

    # ------------------- [3/4] 构建快速查询表 -------------------
    print("[3/4] 构建 (undertone, lightness) → 产品索引 查询表...")
    lookup: dict[str, list[int]] = {}
    for idx, (u, l) in enumerate(zip(undertone_encoded, lightness_encoded)):
        key = f"{int(u)}_{int(l)}" # 如 "0_2" = cool + light
        lookup.setdefault(key, []).append(idx)
    # 转成 numpy 数组（便于检索时索引）
    lookup_np = {key: np.array(vals, dtype=np.int32) for key, vals in lookup.items()}

    for key, vals in sorted(lookup_np.items()):
        ut, lt = key.split("_")
        print(f" {ID_TO_UNDERTONE[int(ut)]:<8} + {LIGHTNESS_NAMES[int(lt)]:<7}: {len(vals):>5} 个产品")

    # ------------------- [4/4] 保存索引 -------------------
    print(f"[4/4] 保存到: {OUTPUT_NPZ}")
    OUTPUT_NPZ.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUTPUT_NPZ,
        brand_array=brand_array,
        product_array=product_array,
        name_array=name_array,
        hex_array=hex_array,
        rgb_array=rgb_array,
        lab_array=lab_array,
        undertone_encoded=undertone_encoded,
        lightness_encoded=lightness_encoded,
        lookup=lookup_np, # dict[str, np.ndarray]
    )

    meta = {
        "total_products": int(len(df)),
        "undertone_map": UNDERTONE_TO_ID,
        "lightness_names": LIGHTNESS_NAMES,
        "lookup_keys": {k: int(len(v)) for k, v in lookup_np.items()},
        "created_by": "process_skin_tone.py",
    }
    with OUTPUT_META.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("\n[OK] skin_tone 索引生成完成！")
    print(f" brand_array : {brand_array.shape}")
    print(f" product_array : {product_array.shape}")
    print(f" name_array : {name_array.shape}")
    print(f" hex_array : {hex_array.shape}")
    print(f" rgb_array : {rgb_array.shape}")
    print(f" lab_array : {lab_array.shape}")
    print(f" undertone_encoded : {undertone_encoded.shape}")
    print(f" lightness_encoded : {lightness_encoded.shape}")
    print(f" lookup : {len(lookup_np)} 个组合")


if __name__ == "__main__":
    main()
