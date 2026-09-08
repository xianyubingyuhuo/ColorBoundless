# -*- coding: utf-8 -*-
"""
process_base_palette.py
=======================
基础色板（base_palette）数据处理脚本 —— Day 1-2

目标：
    把清洗后的 rgb_cleaned.csv（296,934 个颜色，已含 RGB/HSV/Lab）
    处理成"可检索的结构化索引"，用于快速颜色匹配。

架构原则（来自工业级建议）：
    base_palette 是"大结构化数据" → 纯结构化检索（KMeans + CIEDE2000）
    → 不做 embedding，不进 RAG，LLM 不参与颜色计算

产出（写入 models/vector_store/base_palette_index.npz）：
    - hex_array : (N,) 十六进制颜色
    - rgb_array : (N, 3) RGB 值
    - lab_array : (N, 3) Lab 值（感知均匀，用于色差匹配）
    - hue_group_labels : (N,) 色相族标签（红/橙/黄/绿/青/蓝/紫/粉/灰/黑/白）
    - cluster_labels : (N,) KMeans 簇标签（每个颜色属于哪个簇）
    - cluster_centers : (K, 3) 簇中心（Lab 空间）

为什么这样做？
    1. hue_group：快速按"色系"过滤（用户说"想要红色系"→ 直接筛 hue_group==red）
    2. KMeans：296K 颜色先聚成 200 簇，匹配时先找最近簇，再在簇内精找（快）
    3. Lab 匹配：CIEDE2000 感知均匀，色差算得准
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

# ----------------------------- 路径配置 -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# [注意] 数据源说明：
# 原始 "RGB Color Dataset"（rgb_cleaned.csv）R 通道全 ∈[0,4]，只有绿/青/蓝
# 没有红/黄/紫（美妆核心色系）→ 已弃用并删除。
# 唯一数据源 = generate_full_palette.py 生成的全色域色卡（262,144 色）。
BASE_PALETTE_DIR = PROJECT_ROOT / "data" / "processed" / "base_palette"
INPUT_CSV = BASE_PALETTE_DIR / "full_palette.csv"

OUTPUT_NPZ = PROJECT_ROOT / "models" / "vector_store" / "base_palette_index.npz"
OUTPUT_META = PROJECT_ROOT / "models" / "vector_store" / "base_palette_meta.json"

N_CLUSTERS = 200 # KMeans 簇数量

# 色相族定义（按 hue_deg / saturation / value 分类）
HUE_GROUPS = ["red", "orange", "yellow", "green", "cyan", "blue",
              "purple", "magenta", "gray", "black", "white"]
HUE_GROUP_TO_ID = {name: i for i, name in enumerate(HUE_GROUPS)}


def classify_hue_group(hue: float, sat: float, val: float) -> str:
    """根据 HSV 值给颜色分类到色相族。

    优先级：
        1. 极暗（V<10）→ black
        2. 低饱和（S<8）→ 按亮度分 white / gray
        3. 有颜色 → 按色相环分族
    """
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


def main() -> None:
    print(f"[1/4] 读取清洗数据: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f" 共 {len(df)} 个颜色")

    # ------------------- 提取特征列 -------------------
    hex_array = df["hex"].astype(str).to_numpy()
    rgb_array = df[["r", "g", "b"]].to_numpy(dtype=np.float32)
    lab_array = df[["lab_l", "lab_a", "lab_b"]].to_numpy(dtype=np.float32)
    hue_deg = df["hue_deg"].to_numpy()
    sat = df["saturation"].to_numpy()
    val = df["value"].to_numpy()

    # ------------------- [2/4] 生成色相族标签 -------------------
    print("[2/4] 生成色相族标签...")
    hue_group_labels = np.array(
        [HUE_GROUP_TO_ID[classify_hue_group(h, s, v)]
         for h, s, v in zip(hue_deg, sat, val)],
        dtype=np.int8,
    )
    # 统计每个色相族的数量
    for name in HUE_GROUPS:
        cnt = int((hue_group_labels == HUE_GROUP_TO_ID[name]).sum())
        print(f" {name:<10}: {cnt:>8} 个颜色")

    # ------------------- [3/4] KMeans 聚类（用 Lab） -------------------
    print(f"[3/4] KMeans 聚类 (k={N_CLUSTERS}, 用 Lab 特征)...")
    # Lab 感知均匀，聚类比 RGB 更符合人眼
    kmeans = KMeans(n_clusters=N_CLUSTERS, n_init=3, random_state=42, max_iter=300)
    kmeans.fit(lab_array)
    cluster_labels = kmeans.labels_.astype(np.int32)
    cluster_centers = kmeans.cluster_centers_.astype(np.float32)
    print(f" 聚类完成，{N_CLUSTERS} 个簇中心")

    # ------------------- [4/4] 保存索引 -------------------
    print(f"[4/4] 保存到: {OUTPUT_NPZ}")
    OUTPUT_NPZ.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUTPUT_NPZ,
        hex_array=hex_array,
        rgb_array=rgb_array,
        lab_array=lab_array,
        hue_group_labels=hue_group_labels,
        cluster_labels=cluster_labels,
        cluster_centers=cluster_centers,
    )

    meta = {
        "total_colors": int(len(df)),
        "n_clusters": N_CLUSTERS,
        "hue_groups": HUE_GROUPS,
        "hue_group_counts": {
            name: int((hue_group_labels == HUE_GROUP_TO_ID[name]).sum())
            for name in HUE_GROUPS
        },
        "cluster_centers_lab_shape": list(cluster_centers.shape),
        "created_by": "process_base_palette.py",
    }
    with OUTPUT_META.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("\n[OK] base_palette 索引生成完成！")
    print(f" hex_array : {hex_array.shape}")
    print(f" rgb_array : {rgb_array.shape}")
    print(f" lab_array : {lab_array.shape}")
    print(f" hue_group_labels: {hue_group_labels.shape}")
    print(f" cluster_labels : {cluster_labels.shape}")
    print(f" cluster_centers : {cluster_centers.shape}")


if __name__ == "__main__":
    main()
