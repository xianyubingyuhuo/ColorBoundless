# -*- encoding: utf-8 -*-
"""口红色号库 + CIEDE2000 色差检索（ColorBoundless/beauty/lipstick）
用法:
  from lipstick.shade_library import search_shade, hex2lab, ciede2000
  best = search_shade("#FF4D6D", top_k=3)   # 输入 HEX, 返回库中最接近的色号
"""
import json
from pathlib import Path

import numpy as np

# ----------------------------- 色号库（单一数据源） -----------------------------
# 数据正本: data/shades/shades.json —— beauty 试妆 / 未来 agent 工具 / RAG 三方共用。
# 禁止在代码里再硬编码色号（避免双份数据漂移）。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHADES_JSON = PROJECT_ROOT / "data" / "shades" / "shades.json"


def _load_shades() -> list:
    """模块级加载一次。缺文件 / 缺字段直接报错（fail fast，不静默降级）。"""
    if not SHADES_JSON.exists():
        raise FileNotFoundError(
            f"色号库不存在: {SHADES_JSON}\n"
            "（数据正本在 data/shades/shades.json，请勿在代码里硬编码色号）"
        )
    data = json.loads(SHADES_JSON.read_text(encoding="utf-8"))
    required = {"hex", "name", "tone", "occasion", "desc"}
    for i, item in enumerate(data, 1):
        missing = required - set(item)
        if missing:
            raise KeyError(f"{SHADES_JSON.name} 第 {i} 条缺少字段: {missing}")
    return data


SHADES: list = _load_shades()


def hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)], dtype=float)


def rgb2lab(rgb):
    """标准 sRGB -> CIE Lab（标准范围 L 0-100, a/b -128~127）"""
    r, g, b = np.asarray(rgb, dtype=float) / 255.0

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = lin(r), lin(g), lin(b)
    X = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    Y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    Z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    Xn, Yn, Zn = 0.95047, 1.0, 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t + 16 / 116)

    fx, fy, fz = f(X / Xn), f(Y / Yn), f(Z / Zn)
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b_ = 200 * (fy - fz)
    return np.array([L, a, b_])


def hex2lab(h):
    return rgb2lab(hex2rgb(h))


def ciede2000(lab1, lab2):
    """CIEDE2000 色差公式（国际标准，越小越接近）"""
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cbar = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cbar ** 7 / (Cbar ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360

    dLp = L2 - L1
    dCp = C2p - C1p
    dhp = 0.0
    if C1p * C2p != 0:
        dhp = h2p - h1p
        if dhp > 180:
            dhp -= 360
        elif dhp < -180:
            dhp += 360
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp) / 2)

    Lbp = (L1 + L2) / 2
    Cbp = (C1p + C2p) / 2
    hp = (h1p + h2p) / 2
    if C1p * C2p != 0 and abs(h1p - h2p) > 180:
        hp = (h1p + h2p + 360) / 2 if (h1p + h2p) < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * np.cos(np.radians(hp - 30))
         + 0.24 * np.cos(np.radians(2 * hp))
         + 0.32 * np.cos(np.radians(3 * hp + 6))
         - 0.20 * np.cos(np.radians(4 * hp - 63)))
    dtheta = 30 * np.exp(-((hp - 275) / 25) ** 2)
    RC = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    SL = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    SC = 1 + 0.045 * Cbp
    SH = 1 + 0.015 * Cbp * T
    RT = -np.sin(np.radians(2 * dtheta)) * RC
    return float(np.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2
                         + RT * (dCp / SC) * (dHp / SH)))


def search_shade(query_hex, top_k=3):
    """输入 HEX 色号, 用 CIEDE2000 从色号库筛选最接近的 top_k 个
    返回: [{"hex","name","tone","occasion","emotion","desc","dE"}, ...] 按色差升序
    occasion 为闭集数组（daily/work/date/party/night/formal/photo/all），emotion 为风格词数组
    """
    q_lab = hex2lab(query_hex)
    results = []
    for s in SHADES:
        dE = ciede2000(q_lab, hex2lab(s["hex"]))
        results.append({**s, "dE": round(dE, 2)})
    results.sort(key=lambda x: x["dE"])
    return results[:top_k]


if __name__ == "__main__":
    for q in ["FF4D6D", "A63A2B", "E75480"]:
        print("输入 #%s 最近色号:" % q)
        for r in search_shade(q, top_k=3):
            print("  #%s %s  dE=%.2f  (%s | %s)" % (r["hex"], r["name"], r["dE"],
                  "/".join(r["occasion"]), "/".join(r.get("emotion", []))))
