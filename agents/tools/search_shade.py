# -*- coding: utf-8 -*-
"""工具① search_shade —— 色号检索（agent 的手，选色主链路第一站）

输入输出约定（呼应 agents/prompt.py 的 OUTPUT_CONTRACT）：
    结构化 JSON 进、结构化 JSON 出；数字永远由代码算，LLM 只引用不心算。
依赖方向：
    本模块只依赖 beauty/lipstick/shade_library（算法层），算法层不知道 agent 存在。
"""
import importlib.util
import json
import math
import re
from pathlib import Path

# 6 位 hex 的合法形态：0-9 / a-f / A-F，恰好 6 位
_HEX6 = re.compile(r"^[0-9a-fA-F]{6}$")


def normalize_hex(raw: str) -> str:
    """def 1 · 输入清洗：把随手写的色值统一成内部标准 —— 6 位大写、无 #。

    接受 "#FF4D6D" / "ff4d6d" / "F46"（CSS 三位缩写）/ " #f46 " 之类，
    统一输出 "FF4D6D" 这种内部标准形（shade_library 内部就是 lstrip('#') 后使用）。
    不合格式抛 ValueError，错误信息说人话——上层工具函数负责把它转成 JSON error 字段。
    """
    if not isinstance(raw, str):
        raise ValueError(f"色值必须是字符串，收到 {type(raw).__name__}")
    s = raw.strip().lstrip("#")
    if len(s) == 3:                      # CSS 三位缩写：f46 -> ff4466（每位翻倍）
        s = "".join(ch * 2 for ch in s)
    if not _HEX6.fullmatch(s):
        raise ValueError(f"无效色值: {raw!r}（清洗后 {s!r}，需要 3 或 6 位 hex 字符）")
    return s.upper()


# ---------------------------------------------------------------------------
# 算法层接线：importlib 按路径直载 shade_library.py（cwd 双目录实验的结论落地）
# 为什么不走包导入？from lipstick... 必先执行 lipstick/__init__ -> tryon.py
# -> import torch/cv2 —— 工具①只想算色差，不该背着 BiSeNet 起步。
# 直载只执行 shade_library.py 本体：模块级 _load_shades() 读 shades.json，
# 用 Path(__file__).parents[2] 锚定正本，与 sys.path / cwd 全解耦。
# ---------------------------------------------------------------------------
_CORE_PATH = Path(__file__).resolve().parents[2] / "beauty" / "lipstick" / "shade_library.py"
_core_spec = importlib.util.spec_from_file_location("shade_library_core", _CORE_PATH)
_core = importlib.util.module_from_spec(_core_spec)
_core_spec.loader.exec_module(_core)


def search_shade_tool(raw_hex: str, top_k: int = 3) -> dict:
    """def 2 · 工具① 主函数：脏 hex 进，结构化 JSON 出（LLM 可直接引用）。

    成功: {"ok": true,  "tool": "search_shade",
           "query":  {"hex": "FF4D6D", "lab": [L, a, b]},
           "results": [shades.json 条目 + dE，按 CIEDE2000 升序],
           "error": null}
    失败: {"ok": false, "error": "人话原因", "results": []}
    错误也是 JSON——绝不向 agent / HTTP 层抛异常穿透，
    LLM 拿到 error 字段才知道怎么向用户解释（呼应 prompt.py 输出契约）。
    """
    tool = "search_shade"

    # 1) 输入清洗（def 1 的门卫），失败 -> 错误 JSON
    try:
        hex_std = normalize_hex(raw_hex)
    except ValueError as e:
        return {"ok": False, "tool": tool, "error": str(e), "results": []}

    # 2) top_k 卫生检查：bool 是 int 的子类要排除；范围钳到 [1, 库容量]
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        return {"ok": False, "tool": tool,
                "error": f"top_k 必须是整数，收到 {top_k!r}", "results": []}
    k = max(1, min(top_k, len(_core.SHADES)))

    # 3) 调算法层：CIEDE2000 全库比对，数字永远由代码算
    try:
        rows = _core.search_shade(hex_std, top_k=k)
    except Exception as e:               # 算法层意外错误同样不穿透
        return {"ok": False, "tool": tool, "error": f"检索失败: {e}", "results": []}

    # 4) 组装契约：query 里的 lab 是代码算的物理量，LLM 只准引用不准心算
    lab = [round(float(x), 2) for x in _core.hex2lab(hex_std)]
    # def 17e · 官方覆盖判定（用户 2026-09-13 需求）：官方库只有有限色号（当前 20 条），
    # 查询任意色（如黑色）时最近官方色可能差得很远——必须如实标注"官方无此色号"，
    # 让定制口红/眼影/粉底的任意色链路有意义，而不是硬把红棕系塞给查黑色的用户。
    has_official = bool(rows) and float(rows[0].get("dE", 999.0)) <= 1.0
    rgb255 = [int(hex_std[i:i + 2], 16) for i in (0, 2, 4)]
    gb = _gb_lookup(hex_std, rgb255, lab)
    return {"ok": True, "tool": tool,
            "query": {"hex": hex_std, "lab": lab,
                      "gb_label": gb["label"], "gb_cn": gb["cn"],
                      "has_official": has_official,
                      "official_threshold_dE": 1.0},
            "results": rows,
            "error": None}


def gb_color_name(rgb255, lab):
    """GB/T 15608《中国颜色体系》近似命名（R-07 口径：现阶段标注体系）。

    输入：rgb255 (3,) 0~255、lab (3,)；输出：{label, cn}。
    修正记录（2026-09-13，用户报错 #000088→"鲜暗红紫"）：
    ① 色调改用 **HSV 色相角**（感知一致）——Lab 色相角在深色区会把蓝判成紫红；
    ② 明度 V = L*/10（感知明度），彩度 = min(20, 0.4·C*)；
    ③ 修饰语互斥：V<3 → 深(Cm≥10)/暗，V≥7.5 → 鲜(Cm≥10)/浅(Cm≥4)/淡，
       中段 → 鲜(Cm≥10)/淡(Cm<4)——消除"鲜暗"矛盾。
    诚实边界：近似换算，精确标号以《中国颜色体系》国家标准样册为准。
    """
    r, g, b = [v / 255.0 for v in rgb255]
    mx, mn = max(r, g, b), min(r, g, b)
    h = 0.0
    if mx != mn:
        d = mx - mn
        if mx == r:   h = ((g - b) / d) % 6
        elif mx == g: h = (b - r) / d + 2
        else:         h = (r - g) / d + 4
        h *= 60.0                                   # HSV 色相角（感知色调）
    idx = int(h // 36.0) % 10
    pos = (h - idx * 36.0) / 36.0
    hue_num = 10 if pos >= 0.5 else 5

    L, a, bb = float(lab[0]), float(lab[1]), float(lab[2])
    C = math.hypot(a, bb)
    V = max(0.0, min(10.0, L / 10.0))
    Cm = min(20.0, C * 0.4)

    if C < 2.0:                                     # 非彩色（中性轴）
        label = f"N {V:.1f}/0"
        if V >= 8.5:   cn = "白色"
        elif V >= 7.0: cn = "明灰色"
        elif V >= 5.0: cn = "浅灰色"
        elif V >= 3.0: cn = "中灰色"
        elif V >= 1.0: cn = "暗灰色"
        else:          cn = "黑色"
        return {"label": label, "cn": cn}

    hues = ["红", "黄红", "黄", "绿黄", "绿", "蓝绿", "蓝", "紫蓝", "紫", "红紫"]
    syms = ["R", "YR", "Y", "GY", "G", "BG", "B", "PB", "P", "RP"]
    label = f"{hue_num}{syms[idx]} {V:.1f}/{Cm:.1f}"

    if V < 3.0:                                     # 暗区：深（彩度高）/ 暗
        cn = f"深{hues[idx]}" if Cm >= 10 else f"暗{hues[idx]}"
    elif V >= 7.5:                                  # 亮区：鲜（彩度高）/ 浅 / 淡
        cn = f"鲜{hues[idx]}" if Cm >= 10 else (f"浅{hues[idx]}" if Cm >= 4 else f"淡{hues[idx]}")
    else:                                           # 中段：鲜 / 淡 / 无修饰
        cn = f"鲜{hues[idx]}" if Cm >= 10 else (f"淡{hues[idx]}" if Cm < 4 else hues[idx])
    return {"label": label, "cn": cn}


_GBNAMES_JSON = Path(__file__).resolve().parents[2] / "data" / "shades" / "gb_names_16.json"
_COV_CACHE = None         # (官方库条数, items, stats)——shades.json 扩充后自动重算
_COV_MAP = None           # hex → (gb_label, gb_cn)，单色查询懒加载缓存


def _gb_lookup(hex_std, rgb255, lab):
    """GB 命名查询：读 gb_names_16.json（与覆盖检查同源）；网格外颜色用函数近似。"""
    global _COV_MAP
    if _COV_MAP is None:
        try:
            data = json.loads(_GBNAMES_JSON.read_text(encoding="utf-8"))
            _COV_MAP = {it["hex"]: (it["gb_label"], it["gb_cn"]) for it in data["items"]}
        except Exception:
            _COV_MAP = {}
    hit = _COV_MAP.get(hex_std)
    if hit:
        return {"label": hit[0], "cn": hit[1]}
    return gb_color_name(rgb255, lab)


def coverage16_tool() -> dict:
    """def 17d · 全色域覆盖检查（职责分离版，用户 2026-09-13 定稿）。

    数据流：
        GB 命名 → data/shades/gb_names_16.json（generate_gb_names_16.py 产物，纯命名）
        官方匹配 → 运行时从 shades.json 逐点 ΔE00 取最近（官方库扩充自动跟随，
                    无需重跑任何生成脚本；结果按官方库条数缓存）
    输出 items = GB 命名字段 + official_hex/official_name/dE/has_official 组合。
    """
    tool = "coverage16"
    global _COV_CACHE
    try:
        gb_data = json.loads(_GBNAMES_JSON.read_text(encoding="utf-8"))
        shades = _core.SHADES

        if _COV_CACHE and _COV_CACHE[0] == len(shades):     # 官方库未变 → 复用缓存
            items, stats = _COV_CACHE[1], _COV_CACHE[2]
        else:
            off_lab = {s["hex"]: list(_core.hex2lab(s["hex"])) for s in shades}
            items, hits = [], 0
            for it in gb_data["items"]:
                lab = list(_core.hex2lab(it["hex"]))
                best_k, best_d = 0, 1e9
                for k, s in enumerate(shades):              # ΔE00 全量取最小（修欧氏背离）
                    dE = float(_core.ciede2000(lab, off_lab[s["hex"]]))
                    if dE < best_d:
                        best_k, best_d = k, dE
                s = shades[best_k]
                has = best_d <= 1.0
                hits += int(has)
                items.append({**it, "official_hex": s["hex"], "official_name": s["name"],
                              "dE": round(best_d, 2), "has_official": has})
            stats = {"total": len(items), "hits": hits, "miss": len(items) - hits,
                     "coverage_pct": round(100.0 * hits / len(items), 2)}
            _COV_CACHE = (len(shades), items, stats)

        return {"ok": True, "tool": tool,
                "query": {"sampling": gb_data["sampling"], "official_shades": len(shades),
                          "threshold_dE": 1.0},
                "results": {**stats, "items": items},
                "error": None}
    except Exception as exc:                                    # 错误不穿透
        return {"ok": False, "tool": tool, "error": str(exc), "results": {}}
