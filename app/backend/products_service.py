# -*- coding: utf-8 -*-
"""def 15d · 商品层：所选色号 → 最近集团商品匹配（有货/可定制判定）+ 定制申请登记。

商品池（region 维度）：
    lip        官方唇色库（beauty/lipstick/shade_library，CIEDE2000 检索）
    foundation 欧莱雅集团粉底库（shades_group npz 168 条，build_shades_kb.py 产物）
判定：最近商品 CIEDE2000 dE ≤ 5.0 → available（有货）；否则 → 可申请定制。
定制申请：追加写入 data/products/custom_requests.json（零依赖，本地 JSON）。
"""
import importlib.util
import json
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = _ROOT / "data" / "products"
_CUSTOM_JSON = _DATA_DIR / "custom_requests.json"
_AVAILABLE_D = 5.0            # dE ≤ 5.0 视为有货（阈值可调）

# 算法层接线（与 agents/tools/search_shade.py 同款 importlib 直载，只取色差计算）
_CORE_PATH = _ROOT / "beauty" / "lipstick" / "shade_library.py"
_core_spec = importlib.util.spec_from_file_location("shade_library_core", _CORE_PATH)
_core = importlib.util.module_from_spec(_core_spec)
_core_spec.loader.exec_module(_core)

# 粉底商品池（复用 foundation_search 的集团白名单与 npz）
from agents.tools.foundation_search import BRANDS as _BRANDS          # noqa: E402
_SHADES_INDEX = _ROOT / "models" / "vector_store" / "shades_group_index.npz"


@lru_cache(maxsize=1)
def _shades_pool() -> list:
    """shades_group npz → 商品条目 [{brand, product, hex, L}]（titles 前缀回品牌名）。"""
    idx = np.load(_SHADES_INDEX, allow_pickle=True)
    pool = []
    for t, h, L in zip(idx["titles"], idx["tags"], idx["levels"]):
        brand = next((b for b in _BRANDS if str(t).startswith(b)), str(t))
        pool.append({"brand": brand, "product": str(t), "hex": str(h), "L": int(L)})
    return pool


def match_product(hex_color: str, region: str = "lip") -> dict:
    """def 15d · 所选色号 → 最近商品 + 有货判定（dE 阈值 _AVAILABLE_D）。"""
    tool = "products_match"
    try:
        hex_std = str(hex_color).strip().lstrip("#").upper()
        if len(hex_std) != 6 or not all(c in "0123456789ABCDEF" for c in hex_std):
            raise ValueError(hex_color)
    except Exception:
        return {"ok": False, "tool": tool, "error": f"色值格式无效: {hex_color!r}", "results": {}}

    lab = list(_core.hex2lab(hex_std))
    try:
        if region == "foundation":
            best, best_d = None, 1e9
            for it in _shades_pool():
                d = float(_core.ciede2000(lab, list(_core.hex2lab(it["hex"]))))
                if d < best_d:
                    best, best_d = it, d
            nearest = {"brand": best["brand"], "product": best["product"],
                       "hex": best["hex"], "L": best["L"], "dE": round(best_d, 2)}
        elif region == "lip":
            rows = _core.search_shade(hex_std, top_k=1)
            s = rows[0] if rows else None
            if not s:
                return {"ok": False, "tool": tool, "error": "唇色库为空", "results": {}}
            nearest = {"brand": "ColorBoundless Official", "product": s["name"],
                       "hex": s["hex"], "dE": round(float(s["dE"]), 2)}
        else:
            return {"ok": False, "tool": tool,
                    "error": f"未知部位: {region}（可用: lip / foundation）", "results": {}}
    except Exception as e:
        return {"ok": False, "tool": tool, "error": f"商品匹配失败: {e}", "results": {}}

    dE = nearest["dE"]
    return {"ok": True, "tool": tool,
            "query": {"hex": hex_std, "region": region, "threshold_dE": _AVAILABLE_D},
            "results": {"nearest": nearest,
                        "available": bool(dE <= _AVAILABLE_D),
                        "verdict": ("有现货——最近集团商品色差很小" if dE <= _AVAILABLE_D
                                    else "无接近现货——可申请定制")},
            "error": None}


def custom_request(hex_color: str, region: str = "lip", note: str = "") -> dict:
    """def 15d · 无现货色号 → 定制申请登记（追加写 data/products/custom_requests.json）。"""
    tool = "products_custom"
    try:
        hex_std = str(hex_color).strip().lstrip("#").upper()
        if len(hex_std) != 6 or not all(c in "0123456789ABCDEF" for c in hex_std):
            raise ValueError(hex_color)
    except Exception:
        return {"ok": False, "tool": tool, "error": f"色值格式无效: {hex_color!r}", "results": {}}
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = json.loads(_CUSTOM_JSON.read_text(encoding="utf-8")) if _CUSTOM_JSON.exists() else []
        rec = {"hex": hex_std, "region": region, "note": str(note)[:200],
               "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
        data.append(rec)
        _CUSTOM_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"ok": True, "tool": tool,
                "results": {"record": rec, "total": len(data),
                            "message": "定制申请已登记，我们会尽快评估该色号"},
                "error": None}
    except Exception as e:
        return {"ok": False, "tool": tool, "error": f"登记失败: {e}", "results": {}}


def list_products(region: str = "foundation") -> dict:
    """def 18a · 产品库全量列表（products 页浏览）。

    lip        官方唇色库 20 色（name/tone/desc 齐全，三方共用单一数据源）
    foundation 集团粉底库 168 条（brand 已从 titles 前缀回填）
    """
    tool = "products_list"
    if region == "foundation":
        items = [{"brand": it["brand"], "product": it["product"], "hex": it["hex"],
                  "L": it["L"], "desc": "欧莱雅集团在售粉底色号"} for it in _shades_pool()]
    elif region == "lip":
        items = [{"brand": "ColorBoundless Official", "product": s["name"], "hex": s["hex"],
                  "tone": s.get("tone", ""), "desc": s.get("desc", "")} for s in _core.SHADES]
    else:
        return {"ok": False, "tool": tool,
                "error": f"未知部位: {region}（可用: lip / foundation）", "results": {}}
    return {"ok": True, "tool": tool, "query": {"region": region},
            "results": {"count": len(items), "items": items}, "error": None}


def list_custom() -> dict:
    """def 15d · 定制申请记录读取（products 页时间线展示，最新在前）。"""
    try:
        data = json.loads(_CUSTOM_JSON.read_text(encoding="utf-8")) if _CUSTOM_JSON.exists() else []
        return {"ok": True, "tool": "products_custom_list",
                "results": {"count": len(data), "records": list(reversed(data))}, "error": None}
    except Exception as e:
        return {"ok": False, "tool": "products_custom_list", "error": f"读取失败: {e}", "results": {}}
