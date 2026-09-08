# -*- coding: utf-8 -*-
"""
embed_cosmetics_kb.py
=====================
把 cosmetics_kb 文本索引（build_cosmetics_kb.py 的产物）向量化，供 RAG 语义检索。

输入 : models/vector_store/cosmetics_kb_index.npz （retrieval_texts）
输出 : models/vector_store/cosmetics_kb_embeddings.npz
        - embeddings : (N, 512) bge-small-zh-v1.5 归一化向量（余弦相似度 = 点积）
        - row_ids : (N,) 指回 index.npz 的行号（0..N-1）

附带检索自测：用一条典型口语 query（"黄皮涂什么口红显白"）验证语义空间可用。

用法：
    python scripts/embed_cosmetics_kb.py
    （自动优先 GPU，失败回退 CPU；与 embed_style_recommendations.py 同款管线）
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

# ----------------------------- 路径配置 -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_NPZ = PROJECT_ROOT / "models" / "vector_store" / "cosmetics_kb_index.npz"
OUTPUT_NPZ = PROJECT_ROOT / "models" / "vector_store" / "cosmetics_kb_embeddings.npz"

# bge-small-zh-v1.5 模型（本地路径，与 embed_style_recommendations.py 保持一致）
MODEL_PATH = Path(r"e:\作业\vscoding学习\models\bge-small-zh-v1.5")

BATCH_SIZE = 64 # 分批大小（防止 GPU OOM）

# 检索自测 query（口语 → 应命中 undertone/vocab 相关条目）
TEST_QUERIES = [
    "黄皮涂什么颜色的口红显白",
    "色盲怎么知道口红是什么颜色",
    "晚宴妆怎么配色",
]


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


def self_test(
    query: str,
    query_vec: np.ndarray,
    embeddings: np.ndarray,
    titles: np.ndarray,
    ids: np.ndarray,
    top_k: int = 3,
) -> None:
    """点积检索自测（条目量 < 1 万直接全量算）"""
    sims = embeddings @ query_vec # (N,) 归一化后点积 = 余弦
    top_idx = np.argsort(-sims)[:top_k]
    print(f"\n query: 「{query}」")
    for rank, i in enumerate(top_idx, start=1):
        print(f" Top{rank} [{sims[i]:.3f}] {ids[i]} {titles[i]}")


def main() -> None:
    # ---------- 1. 加载文本索引 ----------
    print(f"[1/3] 加载索引: {INDEX_NPZ}")
    if not INDEX_NPZ.exists():
        raise SystemExit(f"[NG] 找不到 {INDEX_NPZ}\n 请先运行 scripts/build_cosmetics_kb.py")
    data = np.load(INDEX_NPZ, allow_pickle=True)
    texts = data["retrieval_texts"]
    ids = data["ids"]
    titles = data["titles"]
    n = len(texts)
    print(f" 共 {n} 条检索文本")

    # ---------- 2. 向量化 ----------
    print("[2/3] 加载 bge-small-zh-v1.5...")
    from sentence_transformers import SentenceTransformer

    device = get_device()
    model = SentenceTransformer(str(MODEL_PATH), device=device)

    print(f"[2/3] 向量化（batch={BATCH_SIZE}，共 {n} 条）...")
    embeddings = model.encode(
        texts.tolist(),
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True, # bge 推荐归一化，余弦相似度 = 点积
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)
    print(f" embeddings shape: {embeddings.shape}")

    # ---------- 3. 检索自测 + 保存 ----------
    print("[3/3] 检索自测（口语 query → top3）...")
    query_vecs = model.encode(
        TEST_QUERIES, batch_size=8, normalize_embeddings=True,
        show_progress_bar=False,
    )
    for q, qv in zip(TEST_QUERIES, np.asarray(query_vecs, dtype=np.float32)):
        self_test(q, qv, embeddings, titles, ids)

    print(f"\n[3/3] 保存到: {OUTPUT_NPZ}")
    np.savez_compressed(
        OUTPUT_NPZ,
        embeddings=embeddings,
        row_ids=np.arange(n, dtype=np.int32),
    )
    print("\n[OK] cosmetics_kb 语义向量生成完成！")
    print(f" embeddings: {embeddings.shape} (float32)")
    print(f" row_ids : {n} 条 → 指回 cosmetics_kb_index.npz")


if __name__ == "__main__":
    main()
