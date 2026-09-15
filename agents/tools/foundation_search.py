# -*- coding: utf-8 -*-
"""def 23 · foundation_search —— 集团粉底色号推荐（向量检索 + 结构化过滤）

数据：models/vector_store/shades_group_*.npz（build_shades_kb.py 产物，168 条）
链路：bge 编码 query → 与库内向量点积（=余弦）→ brand/shade_level 结构化过滤 → top-k
定位：def 15 聚合式试妆的 foundation 模块推荐池（欧莱雅集团四品牌真实粉底产品线，
      L 明度 14-95 与肤色深浅直接联动）。
安全呼应：只推集团品牌（BRANDS 白名单），竞品与外部数据永不出现在结果中。
"""
from functools import lru_cache
from pathlib import Path

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INDEX_NPZ = _PROJECT_ROOT / "models" / "vector_store" / "shades_group_index.npz"
_EMBED_NPZ = _PROJECT_ROOT / "models" / "vector_store" / "shades_group_embeddings.npz"
_MODEL_PATH = Path(r"e:\作业\vscoding学习\models\bge-small-zh-v1.5")

BRANDS = ["Maybelline", "Lancôme", "Make Up For Ever", "L'Oréal"]
_LEVEL_RANGES = {"light": (70, 101), "medium": (40, 70), "deep": (0, 40)}

# def 23 · 参数容错：LLM（尤其关思维链后）可能传中文/别名——清洗后再校验
_BRAND_ALIAS = {
    "兰蔻": "lancôme", "欧莱雅": "l'oréal", "巴黎欧莱雅": "l'oréal",
    "美宝莲": "maybelline", "浮生若梦": "make up for ever", "mufe": "make up for ever",
    "make up for ever": "make up for ever", "makeupforever": "make up for ever",
    "loreal": "l'oréal", "l'oreal": "l'oréal", "loreal paris": "l'oréal",
}
_LEVEL_ALIAS = {
    "浅": "light", "偏白": "light", "白皙": "light", "浅色": "light",
    "中": "medium", "中等": "medium", "自然": "medium", "中浅": "medium", "中深": "medium",
    "深": "deep", "偏深": "deep", "小麦": "deep", "较深": "deep", "深色": "deep",
}


def _level_desc(L: int) -> str:
    if L >= 70:
        return "浅色（适配白皙/浅肤色）"
    if L >= 40:
        return "中等色（适配自然/中等肤色）"
    return "深色（适配小麦/深肤色）"


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer   # 延迟导入，不拖累冷启动
    if not _MODEL_PATH.exists():
        raise FileNotFoundError(f"bge 模型不存在: {_MODEL_PATH}")
    return SentenceTransformer(str(_MODEL_PATH), device="cpu")


@lru_cache(maxsize=1)
def _load():
    idx = np.load(_INDEX_NPZ, allow_pickle=True)
    emb = np.load(_EMBED_NPZ, allow_pickle=True)["embeddings"].astype(np.float32)
    return idx, emb


def foundation_search_tool(query: str, brand: str = "", shade_level: str = "", top_k: int = 3) -> dict:
    """def 23 · 主函数：需求描述进，集团粉底色号 JSON 出。

    query       自然语言需求（如"黄黑皮想要自然提亮的底妆"）
    brand       可选，限定集团品牌（Maybelline/Lancôme/Make Up For Ever/L'Oréal）
    shade_level 可选，light / medium / deep（按明度档过滤）
    top_k       返回数量，默认 3
    成功: {"ok": true,  "results": [{id,brand,product,hex,L,suit,sim}, ...], "error": null}
    失败: {"ok": false, "error": "人话原因", "results": []}——错误不穿透，规矩同工具①
    """
    tool = "foundation_search"

    try:
        vec = _get_model().encode([str(query or "").strip()], batch_size=1,
                                  normalize_embeddings=True, show_progress_bar=False)
        vec = np.asarray(vec, dtype=np.float32)[0]
    except Exception as e:
        return {"ok": False, "tool": tool, "error": f"向量化失败: {e}", "results": []}

    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        return {"ok": False, "tool": tool, "error": f"top_k 必须是正整数，收到 {top_k!r}", "results": []}

    # def 23 · 参数清洗（中文/别名归一）后校验——LLM 传参容错
    brand_f = _BRAND_ALIAS.get((brand or "").strip(), (brand or "").strip()).lower()
    level_f = _LEVEL_ALIAS.get((shade_level or "").strip(), (shade_level or "").strip()).lower()
    if brand_f and brand_f not in [b.lower() for b in BRANDS]:
        return {"ok": False, "tool": tool,
                "error": f"未知品牌: {brand}（可用: {', '.join(BRANDS)}）", "results": []}
    if level_f and level_f not in _LEVEL_RANGES:
        return {"ok": False, "tool": tool,
                "error": f"未知 shade_level: {shade_level}（可用: light / medium / deep）", "results": []}

    idx, emb = _load()
    sims = emb @ vec
    order = np.argsort(-sims)
    want = max(1, min(top_k, len(idx["ids"])))

    results = []
    for i in order:
        if len(results) >= want:
            break
        i = int(i)
        title = str(idx["titles"][i])                       # "brand product"
        b = next((x for x in BRANDS if title.startswith(x)), title.split(" ")[0])
        L = int(idx["levels"][i])
        if brand_f and b.lower() != brand_f:
            continue
        if level_f and not (_LEVEL_RANGES[level_f][0] <= L < _LEVEL_RANGES[level_f][1]):
            continue
        results.append({
            "id": str(idx["ids"][i]),
            "brand": b,
            "product": title,
            "hex": str(idx["tags"][i]),
            "L": L,
            "suit": _level_desc(L),
            "sim": round(float(sims[i]), 4),
        })

    return {"ok": True, "tool": tool,
            "query": {"text": query, "brand": brand, "shade_level": shade_level},
            "results": results, "error": None}