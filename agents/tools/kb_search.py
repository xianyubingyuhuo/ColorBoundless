# -*- coding: utf-8 -*-
"""工具② kb_search —— 化妆知识库语义检索（RAG 的 R：Retrieval）

输入输出约定与工具①一致：结构化 JSON 进出、错误不抛异常穿透、数字由代码算。
数据依赖（建库管线，改了必须重跑 scripts/embed_cosmetics_kb.py）：
    models/vector_store/cosmetics_kb_index.npz      -> retrieval_texts / ids / titles
    models/vector_store/cosmetics_kb_embeddings.npz -> embeddings (N,512) 归一化 float32
模型约定（与建库脚本同源，换模型两处必须同步改）：
    bge-small-zh-v1.5 本地权重 + encode(normalize_embeddings=True)
    -> 归一化之后 点积 = 余弦相似度，检索只做内积，不用再除模长。
"""
from functools import lru_cache
from pathlib import Path

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INDEX_NPZ = _PROJECT_ROOT / "models" / "vector_store" / "cosmetics_kb_index.npz"
_EMBED_NPZ = _PROJECT_ROOT / "models" / "vector_store" / "cosmetics_kb_embeddings.npz"

# 与建库脚本同款本地模型（与 vLLM 无关：本地 sentence-transformers，R-02 边界内）
_MODEL_PATH = Path(r"e:\作业\vscoding学习\models\bge-small-zh-v1.5")


@lru_cache(maxsize=1)
def _get_model():
    """def 3 支撑 · bge 模型单例（惰性加载 + 缓存）。

    为什么惰性：模型加载要几秒，不该在 import 本模块时就卡住（FastAPI 冷启动遭殃）。
    为什么缓存（lru_cache）：embed_query 每次只编码 1 句话，模型必须全局只加载一次。
    为什么固定 CPU：库仅 10 条、query 仅 1 条，CPU 单条编码约 10ms；
    GPU 的加载/搬运开销反而更高——建库才需要 GPU 批量，检索不需要。
    """
    from sentence_transformers import SentenceTransformer   # 延迟导入，同理不拖累模块导入
    if not _MODEL_PATH.exists():
        raise FileNotFoundError(f"bge 模型不存在: {_MODEL_PATH}")
    return SentenceTransformer(str(_MODEL_PATH), device="cpu")


def embed_query(text: str) -> np.ndarray:
    """def 3 · 把一句话编码成 512 维归一化向量（这句话在语义空间的坐标）。

    与建库管线『三同』：同模型 / 同归一化 / 同 float32 —— 三同不齐，检索全是噪音。
    返回 shape (512,) float32，L2 范数 = 1.0（归一化的可直接验）。
    非法输入抛 ValueError，由 def 4 主函数转成 JSON error（工具①立的规矩）。
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("query 必须是非空字符串")
    vec = _get_model().encode(
        [text.strip()],
        batch_size=1,
        normalize_embeddings=True,       # 与建库同款归一化，点积即余弦
        show_progress_bar=False,
    )
    return np.asarray(vec, dtype=np.float32)[0]


# ---------------------------------------------------------------------------
# 库数据接线：两个 npz 都很小（10 条），模块级一次读入内存即可，
# 不配惰性待遇（那是几秒级的大模型才需要的）。
# ---------------------------------------------------------------------------
_INDEX = np.load(_INDEX_NPZ, allow_pickle=True)
_EMBED = np.load(_EMBED_NPZ, allow_pickle=True)["embeddings"].astype(np.float32)


def kb_search_tool(text: str, top_k: int = 3) -> dict:
    """def 4 · 工具② 主函数：一句话进，知识条目 JSON 出（RAG 的 R）。

    成功: {"ok": true,  "tool": "kb_search",
           "query":  {"text": "..."},
           "results": [{id,title,content,tags,sources,sim}, ...] 按 sim 降序,
           "error": null}
    失败: {"ok": false, "error": "人话原因", "results": []}
    规矩与工具①完全一致：错误不穿透，sim 由代码算、LLM 只引用。
    """
    tool = "kb_search"

    # 1) query 向量化（def 3），失败 -> 错误 JSON
    try:
        vec = embed_query(text)
    except Exception as e:                   # 空输入 / 模型缺失 都在这被拦住
        return {"ok": False, "tool": tool, "error": f"向量化失败: {e}", "results": []}

    # 2) top_k 卫生检查（工具①同款规矩：bool 排除、范围钳制）
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        return {"ok": False, "tool": tool,
                "error": f"top_k 必须是整数，收到 {top_k!r}", "results": []}
    n = _EMBED.shape[0]
    k = max(1, min(top_k, n))

    # 3) 检索：归一化向量的点积 = 余弦相似度；降序取 top-k
    sims = _EMBED @ vec
    order = np.argsort(-sims)[:k]

    # 4) 组装契约：np.int32/np.float32 一律转原生类型，否则 json.dumps 会炸
    results = []
    for i in order:
        i = int(i)
        results.append({
            "id": str(_INDEX["ids"][i]),
            "title": str(_INDEX["titles"][i]),
            "content": str(_INDEX["contents"][i]),
            "tags": str(_INDEX["tags"][i]),
            "sources": str(_INDEX["sources"][i]),
            "sim": round(float(sims[i]), 4),
        })
    return {"ok": True, "tool": tool,
            "query": {"text": text.strip()},
            "results": results,
            "error": None}
