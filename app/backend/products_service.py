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
import random
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


def _showcase_owners(hex_std: str) -> list:
    """def 46c · 商品色 hex → 橱窗归属反查（精确命中；橱窗色板与匹配池同源，必可回溯）。
    返回 [{category: 品类中文名, item: 橱窗分支名, shade: 色号名}]（跨品类同色可多条）。"""
    h = str(hex_std).strip().lstrip("#").upper()   # npz 粉底池 hex 为小写——统一大写再比对
    owners = []
    for it in _showcase_items():
        for s in it["shades"]:
            if str(s["hex"]).upper() == h:
                owners.append({"category": _cn(it["category"]), "item": it["name"],
                               "shade": s["name"]})
                break
    return owners


def _owner_label(o: dict) -> str:
    """def 46c · 归属条目 → 展示文本；item 名已含品类词时不再重复前缀。"""
    name = o["item"]
    return name if o["category"] in name else f"{o['category']} · {name}"


def _top_candidates(pool, lab, n=5, official=False):
    """def 56 · 池内 top-N 最近候选（定制弹窗的「选择商品」列表）。
    official=True 的池（眼影/眉妆内建命名盘）没有 brand/product 字段，
    用 name 当系列名、品牌统一为 ColorBoundless Official。"""
    scored = sorted(pool, key=lambda it: float(
        _core.ciede2000(lab, list(_core.hex2lab(it["hex"])))))
    out = []
    for it in scored[:n]:
        d = float(_core.ciede2000(lab, list(_core.hex2lab(it["hex"]))))
        rec = dict(it)
        if official:
            rec["brand"] = "ColorBoundless Official"
            rec["product"] = it.get("name", it.get("product", ""))
        rec["dE"] = round(d, 2)
        out.append(rec)
    return out


def match_product(hex_color: str, region: str = "lip") -> dict:
    """def 15d/46c · 所选色号 → 最近商品 + 有货判定（dE 阈值 _AVAILABLE_D）；
    results 附 showcase/showcase_txt——最近商品色在商品橱窗中的归属（品类 · 分支 · 色号）。
    def 56 · results 附 candidates（top5 近似候选）——定制弹窗「选择商品」的数据源。"""
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
            cands = _top_candidates(_shades_pool(), lab, official=False)
            nearest = {"brand": cands[0]["brand"], "product": cands[0]["product"],
                       "hex": cands[0]["hex"], "L": cands[0].get("L"), "dE": cands[0]["dE"]}
        elif region == "blush":
            cands = _top_candidates(_BLUSH_POOL, lab, official=False)
            nearest = {"brand": cands[0]["brand"], "product": cands[0]["product"],
                       "hex": cands[0]["hex"], "dE": cands[0]["dE"]}
        elif region == "lip":
            rows = _core.search_shade(hex_std, top_k=5)
            if not rows:
                return {"ok": False, "tool": tool, "error": "唇色库为空", "results": {}}
            cands = [{"brand": "ColorBoundless Official", "product": s["name"],
                      "hex": s["hex"], "dE": round(float(s["dE"]), 2)} for s in rows]
            nearest = dict(cands[0])
        elif region == "eyeshadow":
            cands = _top_candidates(_EYESHADOW_POOL, lab, official=True)
            nearest = {"brand": cands[0]["brand"], "product": cands[0]["product"],
                       "hex": cands[0]["hex"], "dE": cands[0]["dE"]}
        elif region == "brow":
            cands = _top_candidates(_BROW_POOL, lab, official=True)
            nearest = {"brand": cands[0]["brand"], "product": cands[0]["product"],
                       "hex": cands[0]["hex"], "dE": cands[0]["dE"]}
        else:
            return {"ok": False, "tool": tool,
                    "error": f"未知部位: {region}（可用: lip / foundation / eyeshadow / brow / blush）", "results": {}}
    except Exception as e:
        return {"ok": False, "tool": tool, "error": f"商品匹配失败: {e}", "results": {}}

    dE = nearest["dE"]
    owners = _showcase_owners(nearest["hex"])   # def 46c · 归属按最近商品色反查（非查询色）
    return {"ok": True, "tool": tool,
            "query": {"hex": hex_std, "region": region, "threshold_dE": _AVAILABLE_D},
            "results": {"nearest": nearest,
                        "candidates": cands,
                        "available": bool(dE <= _AVAILABLE_D),
                        "verdict": ("有现货——最近集团商品色差很小" if dE <= _AVAILABLE_D
                                    else "无接近现货——可申请定制"),
                        "showcase": owners,
                        "showcase_txt": ("；".join(
                            f"{_owner_label(o)} · {o['shade']}" for o in owners)
                            or "（暂未在橱窗系列陈列）")},
            "error": None}


def custom_request(hex_color: str, region: str = "lip", note: str = "",
                   product: str = "", series: str = "", spec: str = "") -> dict:
    """def 15d · 无现货色号 → 定制申请登记（追加写 data/products/custom_requests.json）。
    def 56 · 弹窗选择流新增三个字段：product（定制商品）、series（系列名）、spec（规格）。"""
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
               "product": str(product)[:120], "series": str(series)[:120],
               "spec": str(spec)[:60],
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





def reset_custom() -> None:
    """def 50 · 后端重启即清定制申请时间线（用户 2026-09-22：重启 = 全新演示态）。
    由启动钩子 main.lifespan 调用；格式与 list_custom 的空态读取兼容（"[]"）。"""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _CUSTOM_JSON.write_text("[]", encoding="utf-8")
    except Exception:
        pass


def list_custom() -> dict:

    """def 15d · 定制申请记录读取（products 页时间线展示，最新在前）。"""

    try:

        data = json.loads(_CUSTOM_JSON.read_text(encoding="utf-8")) if _CUSTOM_JSON.exists() else []

        return {"ok": True, "tool": "products_custom_list",

                "results": {"count": len(data), "records": list(reversed(data))}, "error": None}

    except Exception as e:

        return {"ok": False, "tool": "products_custom_list", "error": f"读取失败: {e}", "results": {}}


# def 46 · 橱窗随机分配用固定种子：数量与组合随机错落（真实货架感），但每次启动/刷新
# 完全一致——答辩演示可复现、compare_library 对比库色源不漂移；换种子即换一批布局。
_SHOWCASE_SEED = 89   # 扫描选定：各品类内色数互不重复、错落感最强（3 色小样 ↔ 7 色大系列）


def _wants(rng, n, lo, hi, cap):
    """n 个窗口的随机色数（lo~hi），总和超池容量 cap 时从最多的窗口往回削。"""
    w = [rng.randint(lo, hi) for _ in range(n)]
    while sum(w) > cap:
        i = max(range(n), key=lambda k: w[k])
        if w[i] <= lo:
            break
        w[i] -= 1
    return w


def _deal_shades(rng, pool, wants):
    """洗牌副本 → 按 wants 依次切窗（末窗 clamp，池尽即止；窗口间颜色不重复）。"""
    pool = list(pool)
    rng.shuffle(pool)
    out, start = [], 0
    for w in wants:
        take = min(w, len(pool) - start)
        if take <= 0:
            break
        out.append(pool[start:start + take])
        start += take
    return out


@lru_cache(maxsize=1)
def _showcase_items() -> list:
    """def 46 · 橱窗窗口构造：catalog（展示）与 compare_library（对比库）共用此单一数据源，
    两边永不失同步。每款商品的颜色数量随机错落——真实货架上有的系列 30+ 色、有的仅 2 色，
    不再是旧版「每款恰好对半」的均匀切分；窗口间颜色不重复。粉底按集团品牌各成一款
    （Fit Me / Ultra HD / Teint Idole / True Match），其余品类为官方/内建池洗牌分窗。"""
    rng = random.Random(_SHOWCASE_SEED)
    items = []

    # 口红：官方唇色库 20 色 → 4 款系列（各 3~7 色随机）
    lip = [{"hex": s["hex"], "name": s["name"], "tone": s.get("tone", ""),
            "desc": s.get("desc", "")} for s in _core.SHADES]
    for i, shades in enumerate(_deal_shades(rng, lip, _wants(rng, 4, 3, 7, len(lip))), 1):
        items.append({"id": f"lip{i}", "name": f"丝绒唇膏 · 系列 {i}", "category": "lip",
                      "desc": "官方唇色库随机抽样组合", "shades": shades})

    # 粉底：集团库 168 条按品牌各成一款（22~36 色——真实粉底系列普遍 20~40 色）
    fd_by_brand = {}
    for it in _shades_pool():
        fd_by_brand.setdefault(it["brand"], []).append(
            {"hex": it["hex"], "name": it["product"], "brand": it["brand"], "L": it["L"]})
    fd_names = {"Maybelline": "Fit Me 柔雾粉底", "Make Up For Ever": "Ultra HD 高清粉底",
                "Lancôme": "Teint Idole 持妆粉底", "L'Oréal": "True Match 绝配无瑕粉底"}
    fi = 0
    for brand, pool in fd_by_brand.items():
        take = min(rng.randint(22, 36), len(pool))
        rng.shuffle(pool)
        fi += 1
        items.append({"id": f"foundation{fi}", "name": f"{fd_names.get(brand, brand)}（{brand}）",
                      "category": "foundation", "desc": f"{brand} · 集团粉底库系列抽样",
                      "shades": pool[:take]})

    # 眼影：内建十二色命名盘 → 3 款盘（各 3~6 色，真实眼影盘每盘色数少）
    eye = [dict(it) for it in _EYESHADOW_POOL]
    for i, shades in enumerate(_deal_shades(rng, eye, _wants(rng, 3, 3, 6, len(eye))), 1):
        items.append({"id": f"eyeshadow{i}", "name": f"眼影盘 · 系列 {i}", "category": "eyeshadow",
                      "desc": "内建命名盘抽样组合（大地/玫瑰/紫灰）", "shades": shades})

    # 眉妆：内建五色盘 → 2 款（各 2~4 色，眉部色号本就少）
    brow = [dict(it) for it in _BROW_POOL]
    for i, shades in enumerate(_deal_shades(rng, brow, _wants(rng, 2, 2, 4, len(brow))), 1):
        items.append({"id": f"brow{i}", "name": f"眉笔 · 系列 {i}", "category": "brow",
                      "desc": "五色眉妆盘抽样（深棕/灰黑为主）", "shades": shades})

    # 腮红：演示池 5 色 → 2 款（各 2~4 色）
    blush = [{"hex": it["hex"], "name": it["product"], "brand": it["brand"],
              "desc": it["desc"]} for it in _BLUSH_POOL]
    for i, shades in enumerate(_deal_shades(rng, blush, _wants(rng, 2, 2, 4, len(blush))), 1):
        items.append({"id": f"blush{i}", "name": f"腮红 · 系列 {i}", "category": "blush",
                      "desc": "腮红演示池随机抽样（裸粉→陶土珊瑚）", "shades": shades})

    return items


def catalog() -> dict:
    """def 18d/46 · 商品橱窗：每品类多款商品（唇 4 / 粉底 4 / 眼影 3 / 眉 2 / 腮红 2），
    每款颜色数量随机错落（固定种子可复现，见 _showcase_items）；
    图片为收集占位图（app/frontend/assets/）；ingredients/ratio 为详情页占位——
    为 v3「询问 AI 是否健康 / 成分表的作用」预留接入点。
    """
    tool = "products_catalog"
    _IMG = {"lip": "/assets/lipstick_placeholder.jpg",
            "foundation": "/assets/foundation_placeholder.jpg",
            "eyeshadow": "/assets/eyeshadow_placeholder.jpg",
            "brow": "/assets/brow_placeholder.jpg",
            "blush": "/assets/blush_placeholder.jpg"}
    items = []
    for it in _showcase_items():
        row = dict(it)
        row["img"] = _IMG[it["category"]]
        row["count"] = len(it["shades"])
        row["ingredients"] = "成分表整理中——v3 将接入「询问 AI 是否健康 / 成分表的作用」"
        row["ratio"] = "色粉/基质配比资料整理中（演示占位）"
        items.append(row)
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
    # def 46 · 色源=橱窗窗口（_showcase_items 单一数据源，与商品橱窗永不失同步）
    groups = [(it["category"], it["name"],
               [{"hex": s["hex"], "name": s["name"], "brand": s.get("brand", "")}
                for s in it["shades"]]) for it in _showcase_items()]
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
