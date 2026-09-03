# -*- coding: utf-8 -*-
"""
verify_indexes.py
=================
验证三个数据处理索引是否可用 —— Day 5（整体流程雏形）

验证内容：
    1. base_palette         ：按色相族检索 + 用 Lab 找"最接近指定颜色"的颜色
    2. skin_tone            ：用 (undertone, lightness) 查询表快速圈定产品
    3. style_recommendations：用核心特征组合查规则 + 展示一条自然语言规则

运行：
    python scripts/verify_indexes.py
"""
from __future__ import annotations

import sys

# Windows 终端默认 GBK 编码打不出 emoji（如 ✅），强制用 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VECTOR_STORE = PROJECT_ROOT / "models" / "vector_store"


def load_index(name: str) -> dict:
    """加载 npz 索引（allow_pickle=True 以支持 dict 类型）"""
    data = np.load(VECTOR_STORE / f"{name}.npz", allow_pickle=True)
    return {k: data[k] for k in data.files}


def lab_distance(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """Lab 空间欧氏距离（CIEDE2000 的简化近似，已足够"感知均匀"）"""
    return np.sqrt(np.sum((lab1 - lab2) ** 2, axis=-1))


def verify_base_palette() -> None:
    print("=" * 60)
    print("[1] base_palette 验证")
    print("=" * 60)
    idx = load_index("base_palette_index")

    hue_groups = ["red", "orange", "yellow", "green", "cyan", "blue",
                  "purple", "magenta", "gray", "black", "white"]

    # --- 1a. 按色相族检索：找所有红色系 ---
    red_label = hue_groups.index("red")
    red_mask = idx["hue_group_labels"] == red_label
    red_hex = idx["hex_array"][red_mask]
    print(f"\n红色系颜色: {red_mask.sum()} 个")
    print(f"  示例: {red_hex[:5].tolist()}")

    # --- 1b. Lab 找最接近的颜色：目标 = 经典正红 (255, 0, 0) ---
    target_rgb = np.array([[255, 0, 0]], dtype=np.float32)  # 正红
    # 注意：索引里 lab 是标准 Lab，这里需要把 target 也转成 Lab。
    # 简便起见，直接用索引里的 rgb 做最近邻演示 + Lab 精查。
    # 先用 hue_group 过滤出红色系，再在 Lab 里找最近
    lab_candidates = idx["lab_array"][red_mask]
    # 正红的 Lab 近似值（D65）：L≈53.2, a≈80.1, b≈67.2
    target_lab = np.array([[53.2, 80.1, 67.2]], dtype=np.float32)
    dists = lab_distance(lab_candidates, target_lab)
    best = int(np.argmin(dists))
    best_hex = idx["hex_array"][red_mask][best]
    best_rgb = idx["rgb_array"][red_mask][best]
    print(f"\n目标: 正红 (255,0,0)  → 最近色: {best_hex}  RGB={best_rgb.tolist()}  ΔLab={dists[best]:.1f}")


def verify_skin_tone() -> None:
    print("\n" + "=" * 60)
    print("[2] skin_tone 验证")
    print("=" * 60)
    idx = load_index("skin_tone_index")

    # 查询表：warm(1) + light(2)
    lookup = idx["lookup"].item()
    key = "1_2"
    indices = lookup[key]
    print(f"\nwarm + light 的产品: {len(indices)} 个")
    print("  示例（品牌/产品/色号/hex）:")
    for i in indices[:8]:
        print(f"    {idx['brand_array'][i]} | {idx['product_array'][i]} "
              f"| {idx['name_array'][i]} | {idx['hex_array'][i]}")


def verify_style_recommendations() -> None:
    print("\n" + "=" * 60)
    print("[3] style_recommendations 验证")
    print("=" * 60)
    idx = load_index("style_recommendations_index")

    # 特征名称映射（用于把编码转回可读文本）
    feature_names = idx["feature_names"].item()
    core_features = ["hair_color", "eye_color", "skin_tone", "undertone"]

    def decode(feat: str, code: int) -> str:
        mapping = feature_names[feat]
        for name, c in mapping.items():
            if c == code:
                return name
        return "?"

    # 演示：black发色 + brown眼睛 + medium肤色 + cool色调
    query_codes = [
        feature_names["hair_color"].get("black", 0),
        feature_names["eye_color"].get("brown", 0),
        feature_names["skin_tone"].get("medium", 0),
        feature_names["undertone"].get("cool", 0),
    ]
    key = "_".join(str(c) for c in query_codes)
    lookup = idx["lookup"].item()
    indices = lookup[key]
    print(f"\n特征组合: {[decode(f, c) for f, c in zip(core_features, query_codes)]}")
    print(f"匹配规则: {len(indices)} 条")

    if len(indices) > 0:
        first = int(indices[0])
        print("\n示例规则（自然语言文本，供 RAG/embedding）:")
        print("  " + idx["rule_texts"][first])
        print("\n推荐颜色: " + idx["recommended_colors"][first])
        print("避免颜色: " + idx["avoid_colors"][first])


def verify_semantic_search() -> None:
    print("\n" + "=" * 60)
    print("[4] 语义检索验证（精选 RAG）")
    print("=" * 60)
    from sentence_transformers import SentenceTransformer

    emb_file = VECTOR_STORE / "style_recommendations_embeddings.npz"
    if not emb_file.exists():
        print("  ⚠️ 未找到 embeddings 文件，请先运行 embed_style_recommendations.py")
        return

    embs = np.load(emb_file, allow_pickle=True)
    embeddings = embs["embeddings"]
    rule_ids = embs["rule_ids"]

    idx = load_index("style_recommendations_index")
    rule_texts = idx["rule_texts"]

    # 用 bge 编码查询
    model = SentenceTransformer(
        r"e:\作业\vscoding学习\models\bge-small-zh-v1.5", device="cpu"
    )
    query = "我是黑发、冷白皮，想走甜美温柔的日常妆容，约会用"
    q_vec = model.encode([query], normalize_embeddings=True)[0]

    # 余弦相似度（已归一化 → 点积）
    sims = embeddings @ q_vec
    top_idx = np.argsort(-sims)[:3]

    print(f"\n查询: {query}")
    for rank, i in enumerate(top_idx, 1):
        print(f"\n  Top{rank} (相似度 {sims[i]:.3f}) → 规则 #{rule_ids[i]}:")
        print("   " + rule_texts[i][:120] + "...")


if __name__ == "__main__":
    verify_base_palette()
    verify_skin_tone()
    verify_style_recommendations()
    verify_semantic_search()
    print("\n✅ 四个验证全部完成！")
