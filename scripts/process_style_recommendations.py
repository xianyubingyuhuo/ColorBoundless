# -*- coding: utf-8 -*-
"""
process_style_recommendations.py
================================
个人风格推荐（style_recommendations）数据处理脚本 —— Day 3-4

目标：
    把清洗后的 fashion_style_cleaned.csv（15,120 条风格规则）处理成
    "精选 RAG 索引" + "结构化特征索引"。

架构原则（来自工业级建议）：
    style_recommendations 是系统里"真正的知识库"（用户特征 → 风格/颜色方向）
    → 走 RAG：语义匹配用户需求 → 但必须"少而精"（去重、筛选、控量）

产出（写入 models/vector_store/style_recommendations_index.npz）：
    - feature_encoded : (N, 6) 6 个特征编码（hair/eye/skin/undertone/torso/body）
    - core_encoded : (N, 4) 核心 4 特征编码（hair/eye/skin/undertone）
    - recommended_colors : (N,) 推荐颜色列表（解析后）
    - avoid_colors : (N,) 避免颜色列表（解析后）
    - style_tags : (N,) 推荐风格等标签
    - rule_texts : (N,) 自然语言化规则（供 embedding/RAG）
    - lookup : dict {(hair,eye,skin,undertone): [索引列表]}
    - feature_names : dict 各特征列的取值 → ID 映射

为什么这样做？
    1. 核心 4 特征（发色/眼色/肤色/肤色温度）是用户最常见的输入
    2. rule_texts 把规则转成自然语言，后续可交给 embedding 模型做语义检索
    3. 去重 + 筛选 = "精选"，避免 RAG 塞太多导致幻觉
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------- 路径配置 -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = PROJECT_ROOT / "data" / "processed" / "style_recommendations" / "fashion_style_cleaned.csv"
OUTPUT_NPZ = PROJECT_ROOT / "models" / "vector_store" / "style_recommendations_index.npz"
OUTPUT_META = PROJECT_ROOT / "models" / "vector_store" / "style_recommendations_meta.json"

# 核心特征（用于查询表）+ 扩展特征（用于完整编码）
CORE_FEATURES = ["hair_color", "eye_color", "skin_tone", "undertone"]
ALL_FEATURES = CORE_FEATURES + ["torso_length", "body_proportion"]


def safe_parse_list(s) -> list[str]:
    """把 "['a', 'b']" 字符串解析成列表，失败返回空列表"""
    if isinstance(s, (list, tuple)):
        return [str(x) for x in s]
    try:
        val = ast.literal_eval(str(s))
        if isinstance(val, (list, tuple)):
            return [str(x) for x in val]
        return []
    except (ValueError, SyntaxError):
        return []


def main() -> None:
    print(f"[1/4] 读取清洗数据: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f" 原始 {len(df)} 条规则")

    # ------------------- [2/4] 去重 + 质量筛选（精选） -------------------
    print("[2/4] 去重 + 质量筛选...")
    # 去除完全重复的行
    df = df.drop_duplicates().reset_index(drop=True)
    print(f" 去重后 {len(df)} 条")

    # 质量筛选：必须有推荐色，且核心特征完整
    df["_rec_parsed"] = df["recommended_colors"].apply(safe_parse_list)
    df = df[df["_rec_parsed"].apply(len) > 0].reset_index(drop=True)
    for feat in CORE_FEATURES:
        df = df[df[feat].notna() & (df[feat].astype(str).str.len() > 0)].reset_index(drop=True)
    print(f" 质量筛选后 {len(df)} 条")

    # ------------------- [3/4] 特征编码 -------------------
    print("[3/4] 特征编码 + 文本化...")
    # 用 pandas category 做统一编码（每个特征列的取值 → ID）
    feature_names: dict[str, dict[str, int]] = {}
    feature_encoded = np.zeros((len(df), len(ALL_FEATURES)), dtype=np.int16)
    for j, feat in enumerate(ALL_FEATURES):
        codes, uniques = pd.factorize(df[feat].astype(str))
        feature_encoded[:, j] = codes
        feature_names[feat] = {name: int(i) for i, name in enumerate(uniques)}
        print(f" {feat:<18}: {len(uniques)} 个取值")

    core_encoded = feature_encoded[:, : len(CORE_FEATURES)]

    # 解析推荐色 / 避免色
    recommended_colors = df["_rec_parsed"].apply(lambda x: ";".join(x)).to_numpy()
    avoid_colors = df["avoid_colors"].apply(
        lambda s: ";".join(safe_parse_list(s))).to_numpy()

    # 其他风格标签（拼接成一个字符串，便于展示/检索）
    style_tags = (
        df["recommended_fitting_style"].astype(str)
        + " | " + df["recommended_jewelry_metal"].astype(str)
    ).to_numpy()

    # 生成自然语言规则文本（供 embedding / RAG）
    def to_rule_text(row) -> str:
        rec = safe_parse_list(row["recommended_colors"])
        avo = safe_parse_list(row["avoid_colors"])
        rec_str = "、".join(rec) if rec else "无"
        avo_str = "、".join(avo) if avo else "无"
        return (
            f"用户特征：{row['hair_color']}发色、{row['eye_color']}眼睛、"
            f"{row['skin_tone']}肤色、{row['undertone']}色调、"
            f"{row['torso_length']}、{row['body_proportion']}身形。"
            f"适合颜色：{rec_str}。避免颜色：{avo_str}。"
            f"推荐风格：{row['recommended_fitting_style']}，"
            f"材质：{row['recommended_materials']}，"
            f"图案：{row['recommended_patterns']}，"
            f"首饰金属：{row['recommended_jewelry_metal']}，"
            f"鞋款：{row['recommended_shoes']}。"
        )

    rule_texts = df.apply(to_rule_text, axis=1).to_numpy()

    # 构建核心特征查询表
    lookup: dict[str, list[int]] = {}
    for idx in range(len(df)):
        key = "_".join(str(int(v)) for v in core_encoded[idx])
        lookup.setdefault(key, []).append(idx)
    lookup_np = {key: np.array(vals, dtype=np.int32) for key, vals in lookup.items()}
    print(f" 核心特征组合数: {len(lookup_np)}")

    # ------------------- [4/4] 保存索引 -------------------
    print(f"[4/4] 保存到: {OUTPUT_NPZ}")
    OUTPUT_NPZ.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUTPUT_NPZ,
        feature_encoded=feature_encoded,
        core_encoded=core_encoded,
        recommended_colors=recommended_colors,
        avoid_colors=avoid_colors,
        style_tags=style_tags,
        rule_texts=rule_texts,
        lookup=lookup_np,
        feature_names=feature_names, # dict[str, dict[str, int]]
    )

    meta = {
        "total_rules": int(len(df)),
        "core_features": CORE_FEATURES,
        "all_features": ALL_FEATURES,
        "lookup_keys": int(len(lookup_np)),
        "created_by": "process_style_recommendations.py",
    }
    with OUTPUT_META.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2, default=str)

    print("\n[OK] style_recommendations 索引生成完成！")
    print(f" feature_encoded : {feature_encoded.shape}")
    print(f" core_encoded : {core_encoded.shape}")
    print(f" recommended_colors : {recommended_colors.shape}")
    print(f" avoid_colors : {avoid_colors.shape}")
    print(f" style_tags : {style_tags.shape}")
    print(f" rule_texts : {rule_texts.shape}")
    print(f" lookup : {len(lookup_np)} 个组合")


if __name__ == "__main__":
    main()
