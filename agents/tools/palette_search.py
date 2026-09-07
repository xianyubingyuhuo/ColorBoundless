# -*- coding: utf-8 -*-
"""工具③ palette_search —— 262K 全色域检索（欧氏粗排 + CIEDE2000 精排）

数据依赖（scripts/process_base_palette.py 的产物，字段契约不变则本工具无需改动）：
    models/vector_store/base_palette_index.npz
        hex_array / rgb_array / lab_array / hue_group_labels / cluster_labels / cluster_centers
    models/vector_store/base_palette_meta.json
        hue_groups —— 11 族名表，hue_group_labels 数组元素是它的下标

检索策略：粗排（Lab 欧氏，全库向量化毫秒级）+ 精排（CIEDE2000，只算候选 m 条）。
为什么不用 KMeans 簇硬切：green 族 6.5 万色摊进 200 簇，目标色落在簇边界时
最近邻可能在邻簇，硬切会漏；欧氏粗排窗口 m=5000 与 CIEDE2000 高度相关，
窗口够大就不漏，还省掉簇邻接关系的管理成本。
"""
import importlib.util
import json
from pathlib import Path

import numpy as np

from agents.tools.search_shade import normalize_hex   # 复用工具①的门卫，不复制第二份

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INDEX_NPZ = _PROJECT_ROOT / "models" / "vector_store" / "base_palette_index.npz"
_META_JSON = _PROJECT_ROOT / "models" / "vector_store" / "base_palette_meta.json"

# ---------------------------------------------------------------------------
# 数据接线：262K 行 npz 模块级读入（lab/labels 约 4MB 内存，读一次终身受用）
# ---------------------------------------------------------------------------
_IDX = np.load(_INDEX_NPZ, allow_pickle=True)
_LAB = _IDX["lab_array"].astype(np.float32)
_HUE_LABELS = _IDX["hue_group_labels"].astype(np.int32)

with open(_META_JSON, encoding="utf-8") as _f:
    _META = json.load(_f)
HUE_GROUPS = list(_META["hue_groups"])       # 11 族名表，下标对齐 hue_group_labels

# ---------------------------------------------------------------------------
# 算法层接线：与工具①同款 importlib 直载 shade_library。
# 查询侧 hex2lab 必须与建库侧同公式（lab=f(hex) 铁律）——
# 查询和索引一旦不是同一个转换公式，全库距离都是错位的。
# ---------------------------------------------------------------------------
_CORE_PATH = Path(__file__).resolve().parents[2] / "beauty" / "lipstick" / "shade_library.py"
_core_spec = importlib.util.spec_from_file_location("shade_library_core", _CORE_PATH)
_core = importlib.util.module_from_spec(_core_spec)
_core_spec.loader.exec_module(_core)


def coarse_candidates(lab: np.ndarray, hue_group=None, m: int = 5000) -> np.ndarray:
    """def 5 · 粗排：从 262K 全库筛出欧氏最近的 m 个候选行号。

    lab: (3,) 目标色 Lab（查询侧，def 6 会用 _core.hex2lab 算出来传进来）
    hue_group: None=不限族；或 HUE_GROUPS 之一（"red"/"green"/...）做预筛
    返回: (<=m,) int64 行号数组，按 Lab 平方欧氏距离升序

    欧氏是 CIEDE2000 的廉价替身：高度相关、可全库向量化（262144x3 一次广播运算），
    平方距离不开方——sqrt 保序不保值，排序用不到它，省 26 万次开方。
    非法 hue_group 抛 ValueError，由 def 6 主函数转成 JSON error（工具①立的规矩）。
    """
    if hue_group is not None and hue_group not in HUE_GROUPS:
        raise ValueError(f"hue_group 必须是 {HUE_GROUPS} 之一，收到 {hue_group!r}")

    pool_idx = np.arange(_LAB.shape[0], dtype=np.int64)
    if hue_group is not None:                # 预筛：只在该色相族内比
        pool_idx = pool_idx[_HUE_LABELS == HUE_GROUPS.index(hue_group)]

    d = _LAB[pool_idx] - np.asarray(lab, dtype=np.float32)   # (P, 3) 广播相减
    dist = np.einsum("ij,ij->i", d, d)       # 平方欧氏，向量化、不开方
    order = np.argsort(dist)[: max(1, int(m))]
    return pool_idx[order]


def palette_search_tool(raw_hex: str, hue_group=None, top_k: int = 5,
                        coarse_m: int = 5000) -> dict:
    """def 6 · 工具③ 主函数：目标 hex 进，全色域最接近色 JSON 出。

    成功: {"ok": true,  "tool": "palette_search",
           "query":  {"hex", "lab", "hue_group", "coarse_n"},
           "results": [{hex,rgb,lab,dE,hue_group,cluster}, ...] 按 CIEDE2000 升序,
           "error": null}
    失败: {"ok": false, "error": "人话原因", "results": []}
    规矩与工具①②一致：错误不穿透、数字由代码算、np 类型转原生（json 不炸）。
    """
    tool = "palette_search"

    # 1) hex 清洗：复用工具①的门卫
    try:
        hex_std = normalize_hex(raw_hex)
    except ValueError as e:
        return {"ok": False, "tool": tool, "error": str(e), "results": []}

    # 2) 参数卫生检查（bool 是 int 子类，照旧排除）
    for _name, _val in (("top_k", top_k), ("coarse_m", coarse_m)):
        if not isinstance(_val, int) or isinstance(_val, bool):
            return {"ok": False, "tool": tool,
                    "error": f"{_name} 必须是整数，收到 {_val!r}", "results": []}

    # 3) 查询侧 lab：直载算法层保证与建库同公式
    lab = _core.hex2lab(hex_std)

    # 4) 粗排：262K -> coarse_m 候选（hue_group 非法在这里抛，转 JSON）
    try:
        cand = coarse_candidates(lab, hue_group=hue_group, m=coarse_m)
    except ValueError as e:
        return {"ok": False, "tool": tool, "error": str(e), "results": []}

    k = max(1, min(top_k, len(cand)))

    # 5) 精排：候选内逐条 CIEDE2000（标量公式，5000 次 Python 循环约 0.3s；
    #    慢了再向量化公式或换 argpartition，第一版先跑通速度基线）
    dEs = np.asarray([_core.ciede2000(lab, _LAB[i]) for i in cand], dtype=np.float32)
    top = np.argsort(dEs)[:k]

    # 6) 组装契约：np 类型一律转原生
    results = []
    for j in top:
        row = int(cand[j])
        results.append({
            "hex": str(_IDX["hex_array"][row]),
            "rgb": [int(x) for x in _IDX["rgb_array"][row]],
            "lab": [round(float(x), 2) for x in _LAB[row]],
            "dE": round(float(dEs[j]), 2),
            "hue_group": HUE_GROUPS[int(_HUE_LABELS[row])],
            "cluster": int(_IDX["cluster_labels"][row]),
        })

    return {"ok": True, "tool": tool,
            "query": {"hex": hex_std,
                      "lab": [round(float(x), 2) for x in lab],
                      "hue_group": hue_group if hue_group else "all",
                      "coarse_n": int(len(cand))},
            "results": results,
            "error": None}
