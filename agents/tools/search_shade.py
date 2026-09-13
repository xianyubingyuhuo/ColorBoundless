# -*- coding: utf-8 -*-
"""工具① search_shade —— 色号检索（agent 的手，选色主链路第一站）

输入输出约定（呼应 agents/prompt.py 的 OUTPUT_CONTRACT）：
    结构化 JSON 进、结构化 JSON 出；数字永远由代码算，LLM 只引用不心算。
依赖方向：
    本模块只依赖 beauty/lipstick/shade_library（算法层），算法层不知道 agent 存在。
"""
import importlib.util
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
    gb = gb_color_name(lab)
    return {"ok": True, "tool": tool,
            "query": {"hex": hex_std, "lab": lab,
                      "gb_label": gb["label"], "gb_cn": gb["cn"],
                      "has_official": has_official,
                      "official_threshold_dE": 1.0},
            "results": rows,
            "error": None}


def gb_color_name(lab):
    """GB/T 15608《中国颜色体系》风格近似命名（R-07 口径：现阶段标注体系）。

    输入：Lab (3,)；输出：{label: "5R 4.0/12.0" 标号, cn: "暗红" 中文色名}。
    诚实边界：色调取 Lab 色相角映射 10 基本色调，明度 V ≈ L*/10、彩度 ≈ 0.4·C*
    为近似换算——精确标号以《中国颜色体系》国家标准样册为准（PPT 口径已声明）。
    """
    import math
    L, a, b = float(lab[0]), float(lab[1]), float(lab[2])
    C = math.hypot(a, b)
    h = math.degrees(math.atan2(b, a)) % 360.0
    V = max(0.0, min(10.0, L / 10.0))
    Cm = C * 0.4

    # 中国颜色体系 10 基本色调（每 36° 一档：中心角、中文名、符号）
    hues = [(0, "红", "R"), (36, "黄红", "YR"), (72, "黄", "Y"), (108, "绿黄", "GY"),
            (144, "绿", "G"), (180, "蓝绿", "BG"), (216, "蓝", "B"), (252, "紫蓝", "PB"),
            (288, "紫", "P"), (324, "红紫", "RP")]
    idx = int(((h + 18.0) % 360.0) // 36.0) % 10
    pos = ((h - hues[idx][0]) % 360.0) / 36.0
    hue_num = 10 if pos >= 0.5 else 5
    label_hue = f"{hue_num}{hues[idx][2]}"

    if C < 2.0:                                   # 非彩色（中性轴）
        label = f"N {V:.1f}/0"
        if V >= 8.5:   cn = "白色"
        elif V >= 7.0: cn = "明灰色"
        elif V >= 5.0: cn = "浅灰色"
        elif V >= 3.0: cn = "中灰色"
        elif V >= 1.0: cn = "暗灰色"
        else:          cn = "黑色"
        return {"label": label, "cn": cn}

    if Cm >= 8.0:   cmod = "鲜"
    elif Cm <= 2.0: cmod = "淡"
    else:           cmod = ""
    if V >= 7.5:    vmod = "浅"
    elif V <= 3.0:  vmod = "暗"
    else:           vmod = ""
    cn = f"{cmod}{vmod}{hues[idx][1]}"

    return {"label": f"{label_hue} {V:.1f}/{Cm:.1f}", "cn": cn}


def coverage16_tool() -> dict:
    """def 17d · 全色域覆盖检查：16³=4096 采样点 vs 官方色号库（shades.json）。

    用户需求（2026-09-13）：查询颜色要求全色——16×16×16 采样点每点标注
    "官方色号库是否有这个颜色"（与最近官方色号 ΔE00 ≤ 1.0 → 官方有）。
    用途：暴露官方库（当前 20 条）对全色域的覆盖缺口——缺口清单就是
    色号图片库（extract_palette_from_images 产物）扩充 shades.json 的目标。

    性能：官方库 N 条 × 4096 点，Lab 欧氏全对广播（分块）取最近，再逐点 ΔE00。
    """
    tool = "coverage16"
    try:
        import numpy as np

        shades = _core.SHADES
        if not shades:
            return {"ok": False, "tool": tool, "error": "官方色号库为空", "results": {}}

        off_lab = np.array([_core.hex2lab(s["hex"]) for s in shades], dtype=np.float64)
        levels = [round(i * 255 / 15) for i in range(16)]          # 0,17,...,255
        pts = [(r, g, b) for r in levels for g in levels for b in levels]
        q_lab = np.array([_core.hex2lab("%02X%02X%02X" % pt) for pt in pts], dtype=np.float64)

        best = np.empty(len(q_lab), dtype=np.int64)
        CH = 512
        for s0 in range(0, len(q_lab), CH):                        # 分块广播防内存尖峰
            d = ((q_lab[s0:s0 + CH, None, :] - off_lab[None, :, :]) ** 2).sum(-1)
            best[s0:s0 + CH] = d.argmin(1)

        items, hits = [], 0
        for j, pt in enumerate(pts):
            k = int(best[j])
            s = shades[k]
            dE = float(_core.ciede2000(q_lab[j], off_lab[k]))
            has = dE <= 1.0                                        # ΔE≤1 视为官方有（JND 内）
            hits += int(has)
            gb = gb_color_name(q_lab[j])                           # R-07 · GB/T 15608 近似命名
            items.append({"hex": "%02X%02X%02X" % pt, "rgb": list(pt),
                          "official_hex": s["hex"], "official_name": s["name"],
                          "dE": round(dE, 2), "has_official": has,
                          "gb_label": gb["label"], "gb_cn": gb["cn"]})

        miss = len(items) - hits
        return {"ok": True, "tool": tool,
                "query": {"sampling": "16x16x16=4096", "official_shades": len(shades),
                          "threshold_dE": 1.0},
                "results": {"total": len(items), "hits": hits, "miss": miss,
                            "coverage_pct": round(100.0 * hits / len(items), 2),
                            "items": items},
                "error": None}
    except Exception as exc:                                       # 错误不穿透
        return {"ok": False, "tool": tool, "error": str(exc), "results": {}}
