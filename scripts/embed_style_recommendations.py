# -*- coding: utf-8 -*-
"""
embed_style_recommendations.py
==============================
把 style_recommendations 的规则文本（rule_texts）向量化，供 RAG 语义检索。

背景：
    style_recommendations 是系统里"真正的知识库"（用户特征 → 风格/颜色方向），
    走"精选 RAG"。规则文本（rule_texts）已在上一步生成，这里把它转成向量，
    语义检索才能真正可用。

产出（写入 models/vector_store/style_recommendations_embeddings.npz）：
    - embeddings : (N, 512)  规则文本的向量（bge-small-zh-v1.5，归一化）
    - rule_ids   : (N,)      对应 style_recommendations_index.npz 的行号

用法：
    python scripts/embed_style_recommendations.py
    （自动优先 GPU，失败回退 CPU；分批处理防止显存溢出）
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

# ----------------------------- 路径配置 -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_NPZ = PROJECT_ROOT / "models" / "vector_store" / "style_recommendations_index.npz"
OUTPUT_NPZ = PROJECT_ROOT / "models" / "vector_store" / "style_recommendations_embeddings.npz"

# bge-small-zh-v1.5 模型（本地路径）
MODEL_PATH = Path(r"e:\作业\vscoding学习\models\bge-small-zh-v1.5")

BATCH_SIZE = 64   # 分批大小（防止 GPU OOM）


def get_device() -> str:
    """优先 GPU，失败回退 CPU"""
    try:
        import torch
        if torch.cuda.is_available():
            print(f"使用 GPU: {torch.cuda.get_device_name(0)}")
            return "cuda"
    except Exception as e:
        print(f"GPU 不可用: {e}")
    print("使用 CPU")
    return "cpu"


def main() -> None:
    # ---------- 1. 加载规则文本 ----------
    print(f"[1/3] 加载索引: {INDEX_NPZ}")
    data = np.load(INDEX_NPZ, allow_pickle=True)
    rule_texts = data["rule_texts"]
    n_rules = len(rule_texts)
    print(f"      共 {n_rules} 条规则文本")

    # ---------- 2. 加载模型并向量化 ----------
    print("[2/3] 加载 bge-small-zh-v1.5...")
    from sentence_transformers import SentenceTransformer

    device = get_device()
    model = SentenceTransformer(str(MODEL_PATH), device=device)

    # 分批编码，防止 OOM；normalize 方便用余弦相似度
    print(f"[2/3] 向量化（batch={BATCH_SIZE}，共 {n_rules} 条）...")
    embeddings = model.encode(
        rule_texts.tolist(),
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,  # bge 推荐归一化，用余弦相似度
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)
    print(f"      embeddings shape: {embeddings.shape}")

    # ---------- 3. 保存 ----------
    print(f"[3/3] 保存到: {OUTPUT_NPZ}")
    OUTPUT_NPZ.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUTPUT_NPZ,
        embeddings=embeddings,
        rule_ids=np.arange(n_rules, dtype=np.int32),
    )
    print("\n✅ style_recommendations 语义向量生成完成！")
    print(f"   embeddings: {embeddings.shape} (float32)")
    print(f"   rule_ids  : {n_rules} 条")


if __name__ == "__main__":
    main()
