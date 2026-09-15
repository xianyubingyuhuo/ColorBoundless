# -*- coding: utf-8 -*-
"""def 23 · build_shades_kb：Kaggle shades.csv → 集团粉底知识库（bge 编码 npz）

数据源：download_materials/化妆品/shades.csv（Kaggle Makeup Shades，625 行粉底色号）
清洗规则（与 Kaggle 官方 EDA 一致）：
    1) dropna(H/S/V)——缺失全部来自 Covergirl + Olay（Kaggle notebook 结论）
    2) hex 去重——保留首条
    3) 集团过滤——仅保留欧莱雅集团旗下四品牌（比赛定位：不推竞品）
产出（与 kb_search 加载格式对齐）：
    models/vector_store/shades_group_index.npz     -> ids/titles/contents/tags/sources/levels
    models/vector_store/shades_group_embeddings.npz -> embeddings (N,512) 归一化 float32
检索文本设计：品牌+系列+色值+明度档位（L 与肤色深浅直接联动——粉底推荐的核心特征）。
"""
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

_ROOT = Path(__file__).resolve().parents[1]
_CSV = Path(r"E:\作业\欧莱雅比赛项目\download_materials\化妆品\shades.csv")
_OUT_INDEX = _ROOT / "models" / "vector_store" / "shades_group_index.npz"
_OUT_EMBED = _ROOT / "models" / "vector_store" / "shades_group_embeddings.npz"
_MODEL_PATH = Path(r"e:\作业\vscoding学习\models\bge-small-zh-v1.5")

LOREAL_BRANDS = ["Maybelline", "Lancôme", "Make Up For Ever", "L'Oréal"]


def level_desc(L: float) -> str:
    """明度档位 → 肤色适配描述（L 是粉底推荐的肤色联动核心特征）。"""
    if L >= 80:
        return "浅色（适配白皙/浅肤色）"
    if L >= 60:
        return "中浅色（适配自然偏白肤色）"
    if L >= 40:
        return "中等色（适配自然/中等肤色）"
    if L >= 20:
        return "中深色（适配小麦/较深肤色）"
    return "深色（适配深肤色）"


def main():
    df = pd.read_csv(_CSV)
    n0 = len(df)
    df = df.dropna(subset=["H", "S", "V"])                       # 规则1：与 Kaggle EDA 一致
    df = df.drop_duplicates(subset=["hex"], keep="first")        # 规则2：重复 hex 保留首条
    df = df[df["brand"].isin(LOREAL_BRANDS)].reset_index(drop=True)  # 规则3：仅集团品牌
    print(f"清洗: {n0} -> {len(df)} 条（dropna / 去重 / 集团过滤 {LOREAL_BRANDS}）")

    texts, titles, ids, tags, sources, levels = [], [], [], [], [], []
    for i, r in df.iterrows():
        L = float(r["L"])
        desc = level_desc(L)
        text = (f"{r['brand']} {r['product']} 粉底色号，色值 #{r['hex']}，"
                f"明度 {int(L)}，{desc}")
        texts.append(text)
        titles.append(f"{r['brand']} {r['product']}")
        ids.append(f"{r['brand_short']}_{r['product_short']}_{r['hex']}")
        tags.append(str(r["hex"]))
        sources.append("Kaggle Makeup Shades · L'Oréal Group")
        levels.append(int(L))

    print(f"加载 bge 模型: {_MODEL_PATH}")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(str(_MODEL_PATH), device="cpu")

    print(f"编码 {len(texts)} 条检索文本...")
    emb = model.encode(texts, batch_size=16, normalize_embeddings=True, show_progress_bar=True)
    emb = np.asarray(emb, dtype=np.float32)

    np.savez(_OUT_INDEX, ids=np.array(ids), titles=np.array(titles),
             contents=np.array(texts), tags=np.array(tags),
             sources=np.array(sources), levels=np.array(levels))
    np.savez(_OUT_EMBED, embeddings=emb)
    print(f"完成: {_OUT_INDEX.name} + {_OUT_EMBED.name}（{emb.shape[0]} 条 x {emb.shape[1]} 维）")


if __name__ == "__main__":
    main()