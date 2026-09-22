# -*- coding: utf-8 -*-
"""def 15d · 商品层：所选色号 → 最近集团商品匹配（有货/可定制判定）+ 定制申请登记。

商品池（region 维度）：
    lip        官方唇色库（beauty/lipstick/shade_library，CIEDE2000 检索）
    foundation 欧莱雅集团粉底库（shades_group npz 168 条，build_shades_kb.py 产物）
    blush      内建腮红演示池（5 色号：裸粉→陶土珊瑚，CIEDE2000 最近邻）
判定：最近商品 CIEDE2000 dE ≤ 5.0 → available（有货）；否则 → 可申请定制。
定制申请：追加写入 data/products/custom_requests.json（零依赖，本地 JSON）。
"""
import importlib.util
import uuid
import json
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = _ROOT / "data" / "products"
_CUSTOM_JSON = _DATA_DIR / "custom_requests.json"
_AVAILABLE_D = 5.0            # dE ≤ 5.0 视为有货（阈值可调）

# 腮红商品池（def 18 · 演示用内建小池：真实感腮红色号，冷调裸粉→陶土珊瑚）
_BLUSH_POOL = [
    {"brand": "L'Oréal Paris", "product": "True Match Blush 110 ivory",
     "hex": "EAC7C7", "desc": "冷调裸粉，白皙肌提气色"},
    {"brand": "L'Oréal Paris", "product": "True Match Blush 190 rosy",
     "hex": "E8A0A0", "desc": "经典玫瑰粉，日常百搭"},
    {"brand": "NYX Professional", "product": "Sweet Cheeks SC01",
     "hex": "D98E8E", "desc": "蜜桃粉，暖皮友好"},
    {"brand": "Maybelline", "product": "Fit Me Blush 55 coral",
     "hex": "C97B63", "desc": "陶土珊瑚，深肤色显轮廓"},
    {"brand": "L'Oréal Paris", "product": "Infallible Blush 012 mauve",
     "hex": "B76E79", "desc": "干枯玫瑰，气质挂"},
]

# 眼影商品池（def 18d · 内建十二色命名盘：大地/玫瑰/紫灰，演示用）
_EYESHADOW_POOL = [
        {"hex": "C9A66B", "name": "香槟金", "desc": "提亮眼头"},
        {"hex": "B08968", "name": "焦糖大地", "desc": "日常打底"},
        {"hex": "8A5A44", "name": "深可可", "desc": "加深眼尾"},
        {"hex": "D9B8A6", "name": "裸米", "desc": "大面积铺色"},
        {"hex": "C76B6B", "name": "干玫瑰", "desc": "温柔红调"},
        {"hex": "9E5E6F", "name": "莓果紫", "desc": "约会盘"},
        {"hex": "7A5C77", "name": "灰紫芋泥", "desc": "消肿盘"},
        {"hex": "5C4B56", "name": "暗夜棕紫", "desc": "眼线加深"},
        {"hex": "B7A7C9", "name": "雾霾紫", "desc": "眼中提亮"},
        {"hex": "8E9AAF", "name": "蓝灰", "desc": "冷调盘"},
        {"hex": "C9B27C", "name": "橄榄金", "desc": "健康光泽"},
        {"hex": "3E3A39", "name": "碳黑", "desc": "戏剧眼线"},
]

# 眉妆商品池（def 18h2 · 内建五色命名盘：深棕/灰黑为主，按发色选）
_BROW_POOL = [
        {"hex": "284D42", "name": "松烟深青", "desc": "黑发/深发色定形"},
        {"hex": "3E3A39", "name": "碳灰棕", "desc": "自然加深，冷调发色"},
        {"hex": "5C4033", "name": "深咖", "desc": "棕发通用"},
        {"hex": "8B6F47", "name": "亚麻棕", "desc": "染浅发色提气色"},
        {"hex": "6E4B3A", "name": "红棕", "desc": "红棕/栗色发色"},
]

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
        elif region == "blush":
            best, best_d = None, 1e9
            for it in _BLUSH_POOL:
                d = float(_core.ciede2000(lab, list(_core.hex2lab(it["hex"]))))
                if d < best_d:
                    best, best_d = it, d
            nearest = {"brand": best["brand"], "product": best["product"],
                       "hex": best["hex"], "dE": round(best_d, 2)}
        elif region == "lip":
            rows = _core.search_shade(hex_std, top_k=1)
            s = rows[0] if rows else None
            if not s:
                return {"ok": False, "tool": tool, "error": "唇色库为空", "results": {}}
            nearest = {"brand": "ColorBoundless Official", "product": s["name"],
                       "hex": s["hex"], "dE": round(float(s["dE"]), 2)}
        elif region == "eyeshadow":
            best, best_d = None, 1e9
            for it in _EYESHADOW_POOL:
                d = float(_core.ciede2000(lab, list(_core.hex2lab(it["hex"]))))
                if d < best_d:
                    best, best_d = it, d
            nearest = {"brand": "ColorBoundless Official", "product": best["name"],
                       "hex": best["hex"], "dE": round(best_d, 2)}
        elif region == "brow":
            best, best_d = None, 1e9
            for it in _BROW_POOL:
                d = float(_core.ciede2000(lab, list(_core.hex2lab(it["hex"]))))
                if d < best_d:
                    best, best_d = it, d
            nearest = {"brand": "ColorBoundless Official", "product": best["name"],
                       "hex": best["hex"], "dE": round(best_d, 2)}
        else:
            return {"ok": False, "tool": tool,
                    "error": f"未知部位: {region}（可用: lip / foundation / eyeshadow / brow / blush）", "results": {}}
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
        rec = {"id": uuid.uuid4().hex[:8], "hex": hex_std, "region": region, "note": str(note)[:200],
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

    elif region == "blush":
        items = [{"brand": it["brand"], "product": it["product"], "hex": it["hex"],
                  "desc": it["desc"]} for it in _BLUSH_POOL]
    elif region == "lip":

        items = [{"brand": "ColorBoundless Official", "product": s["name"], "hex": s["hex"],

                  "tone": s.get("tone", ""), "desc": s.get("desc", "")} for s in _core.SHADES]

    elif region == "eyeshadow":
        items = [{"brand": "ColorBoundless Official", "product": it["name"], "hex": it["hex"],
                  "desc": it["desc"]} for it in _EYESHADOW_POOL]
    elif region == "brow":
        items = [{"brand": "ColorBoundless Official", "product": it["name"], "hex": it["hex"],
                  "desc": it["desc"]} for it in _BROW_POOL]
    else:

        return {"ok": False, "tool": tool,

                "error": f"未知部位: {region}（可用: lip / foundation / eyeshadow / brow / blush）", "results": {}}

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


def catalog() -> dict:
    """def 18d · 商品橱窗：每品类多窗口（口红1/2、粉底1/2、眼影1、腮红1），
    色板切片自真实数据池（唇 20 色对半、粉底 168 条隔条抽样、腮红 5 色、眼影内建 12 色）；
    图片为收集占位图（app/frontend/assets/）；ingredients/ratio 为详情页占位——
    为 v3「询问 AI 是否健康 / 成分表的作用」预留接入点。
    """
    tool = "products_catalog"
    lip = list(_core.SHADES)
    fd = _shades_pool()
    items = [
        {"id": "lip1", "name": "口红 1", "category": "lip",
         "img": "/assets/lipstick_placeholder.jpg",
         "desc": "官方唇色库 · 前半系列（正红/豆沙/珊瑚）",
         "shades": [{"hex": s["hex"], "name": s["name"], "tone": s.get("tone", ""),
                     "desc": s.get("desc", "")} for s in lip[: len(lip) // 2]]},
        {"id": "lip2", "name": "口红 2", "category": "lip",
         "img": "/assets/lipstick_placeholder.jpg",
         "desc": "官方唇色库 · 后半系列（玫瑰/浆果/棕调）",
         "shades": [{"hex": s["hex"], "name": s["name"], "tone": s.get("tone", ""),
                     "desc": s.get("desc", "")} for s in lip[len(lip) // 2 :]]},
        {"id": "foundation1", "name": "粉底 1", "category": "foundation",
         "img": "/assets/foundation_placeholder.jpg",
         "desc": "欧莱雅集团粉底 · 均匀抽样 A 组",
         "shades": [{"hex": it["hex"], "name": it["product"], "brand": it["brand"],
                     "L": it["L"]} for it in fd[0::2]]},
        {"id": "foundation2", "name": "粉底 2", "category": "foundation",
         "img": "/assets/foundation_placeholder.jpg",
         "desc": "欧莱雅集团粉底 · 均匀抽样 B 组",
         "shades": [{"hex": it["hex"], "name": it["product"], "brand": it["brand"],
                     "L": it["L"]} for it in fd[1::2]]},
        {"id": "eyeshadow1", "name": "眼影 1", "category": "eyeshadow",
         "img": "/assets/eyeshadow_placeholder.jpg",
         "desc": "内建十二色盘（大地/玫瑰/紫灰）",
         "shades": list(_EYESHADOW_POOL)},
        {"id": "brow1", "name": "眉妆 1", "category": "brow",
         "img": "/assets/brow_placeholder.jpg",
         "desc": "内建五色命名盘（深棕/灰黑为主，按发色选）",
         "shades": [{"hex": it["hex"], "name": it["name"],
                     "desc": it["desc"]} for it in _BROW_POOL]},
        {"id": "blush1", "name": "腮红 1", "category": "blush",
         "img": "/assets/blush_placeholder.jpg",
         "desc": "腮红演示池（冷调裸粉→陶土珊瑚）",
         "shades": [{"hex": it["hex"], "name": it["product"], "brand": it["brand"],
                     "desc": it["desc"]} for it in _BLUSH_POOL]},
    ]
    for it in items:
        it["count"] = len(it["shades"])
        it["ingredients"] = "成分表整理中——v3 将接入「询问 AI 是否健康 / 成分表的作用」"
        it["ratio"] = "色粉/基质配比资料整理中（演示占位）"
    return {"ok": True, "tool": tool,
            "results": {"count": len(items), "items": items}, "error": None}


def cancel_custom(hex_color: str = "", region: str = "", ts: str = "") -> dict:
    """def 18h · 取消定制申请：按 hex+region+ts 组合定位删除（至少给一项，全给最稳）。

    旧记录无 id 字段——用三元组匹配即可唯一定位（ts 精确到秒）。

    """
    tool = "products_custom_cancel"
    try:
        data = json.loads(_CUSTOM_JSON.read_text(encoding="utf-8")) if _CUSTOM_JSON.exists() else []
        hx = str(hex_color or "").strip().lstrip("#").upper()
        rg = str(region or "").strip()
        tsq = str(ts or "").strip()
        if not (hx or rg or tsq):
            return {"ok": False, "tool": tool, "error": "至少提供 hex / region / ts 之一", "results": {}}
        keep, removed = [], 0
        for r in data:
            hit = ((not hx or r.get("hex", "").upper() == hx) and
                   (not rg or r.get("region", "") == rg) and
                   (not tsq or r.get("ts", "") == tsq))
            if hit: removed += 1
            else: keep.append(r)
        if removed == 0:
            return {"ok": False, "tool": tool, "error": "未找到匹配的定制申请", "results": {}}
        _CUSTOM_JSON.write_text(json.dumps(keep, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"ok": True, "tool": tool,
                "results": {"removed": removed, "total": len(keep)}, "error": None}
    except Exception as e:
        return {"ok": False, "tool": tool, "error": f"取消失败: {e}", "results": {}}


def _cn(cat: str) -> str:
    return {"lip": "唇妆", "foundation": "粉底", "eyeshadow": "眼影",
            "brow": "眉妆", "blush": "腮红"}.get(cat, cat)


def _lum(h: str) -> float:
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


@lru_cache(maxsize=1)
def _gb_swatch_index() -> dict:
    """def 18i · 官方色库索引：{hex: gb_cn}（GB 16³=4096 全色域采样）。"""
    path = _ROOT / "data" / "shades" / "gb_names_16.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(it["hex"]).upper(): str(it.get("gb_cn", "")) for it in data.get("items", [])}


def _official_cover(hex6: str) -> bool:
    """def 18i · 官方覆盖判定：精确命中 GB 格点，或其包围 8 邻格点的最近 dE ≤ 1.0
    （与 def 17e「官方有/无」徽章同语义——绿框标记的数据依据）。"""
    idx = _gb_swatch_index()
    h = hex6.upper()
    if h in idx:
        return True
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    step = 17
    best = None
    for rr in sorted({min(255, (r // step) * step), min(255, (r // step + 1) * step)}):
        for gg in sorted({min(255, (g // step) * step), min(255, (g // step + 1) * step)}):
            for bb in sorted({min(255, (b // step) * step), min(255, (b // step + 1) * step)}):
                k = f"{rr:02X}{gg:02X}{bb:02X}"
                if k not in idx:
                    continue
                d = float(_core.ciede2000(list(_core.hex2lab(h)), list(_core.hex2lab(k))))
                if best is None or d < best:
                    best = d
    return best is not None and best <= 1.0


def compare_library() -> dict:
    """def 18i · 对比库：全商品颜色汇集（hex → 有此色的商品清单，跨品类）+ 官方覆盖标记。
    色源 = 全部橱窗窗口的色板；排序按明度（暗→亮）。
    """
    tool = "products_compare"
    lip = list(_core.SHADES)
    fd = _shades_pool()
    groups = [
        ("lip", "口红 1", [{"hex": s["hex"], "name": s["name"]} for s in lip[: len(lip) // 2]]),
        ("lip", "口红 2", [{"hex": s["hex"], "name": s["name"]} for s in lip[len(lip) // 2 :]]),
        ("foundation", "粉底 1", [{"hex": it["hex"], "name": it["product"],
                                   "brand": it["brand"]} for it in fd[0::2]]),
        ("foundation", "粉底 2", [{"hex": it["hex"], "name": it["product"],
                                   "brand": it["brand"]} for it in fd[1::2]]),
        ("eyeshadow", "眼影 1", [{"hex": it["hex"], "name": it["name"]} for it in _EYESHADOW_POOL]),
        ("brow", "眉妆 1", [{"hex": it["hex"], "name": it["name"]} for it in _BROW_POOL]),
        ("blush", "腮红 1", [{"hex": it["hex"], "name": it["product"],
                              "brand": it["brand"]} for it in _BLUSH_POOL]),
    ]
    index = {}
    for cat, item_name, shades in groups:
        for s in shades:
            hx = str(s["hex"]).upper()
            index.setdefault(hx, []).append(
                {"category": cat, "item": item_name, "name": s["name"],
                 "brand": s.get("brand", "")})
    swatches = []
    for hx in sorted(index.keys(), key=_lum):
        prods = index[hx]
        swatches.append({"hex": hx, "count": len(prods),
                         "products": prods,
                         "products_txt": "\n".join(
                             f"{_cn(p['category'])} · {p['item']} · {p['name']}" for p in prods),
                         "official": _official_cover(hx)})
    return {"ok": True, "tool": tool,
            "results": {"count": len(swatches), "swatches": swatches}, "error": None}
