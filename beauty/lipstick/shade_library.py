# -*- encoding: utf-8 -*-
"""口红色号库 + CIEDE2000 色差检索（ColorBoundless/beauty/lipstick）
用法:
  from lipstick.shade_library import search_shade, hex2lab, ciede2000
  best = search_shade("#FF4D6D", top_k=3)   # 输入 HEX, 返回库中最接近的色号
"""
import numpy as np

# 色号库: 每个色号含 HEX / 名称 / 色调 / 场合
SHADES = [
    {"hex": "A63A2B", "name": "复古红棕", "tone": "warm", "occasion": "晚宴/气场",
     "desc": "温暖的红棕色，显白不挑皮"},
    {"hex": "FF4D6D", "name": "元气正红", "tone": "warm", "occasion": "日常/约会",
     "desc": "明亮的正红色，提气色"},
    {"hex": "D81B60", "name": "玫红", "tone": "cool", "occasion": "派对/舞台",
     "desc": "玫粉色，冷调显白"},
    {"hex": "C2185B", "name": "浆果红", "tone": "cool", "occasion": "秋冬/复古",
     "desc": "深浆果色，浓郁有质感"},
    {"hex": "E75480", "name": "蜜桃粉", "tone": "warm", "occasion": "日常/少女",
     "desc": "柔和蜜桃粉，清透自然"},
    {"hex": "B22222", "name": "正宫红", "tone": "warm", "occasion": "正式/通勤",
     "desc": "经典正红，端庄大气"},
    {"hex": "8E2A3A", "name": "红酒", "tone": "cool", "occasion": "晚宴/高冷",
     "desc": "深沉酒红色，高级感"},
    {"hex": "DB7093", "name": "豆沙粉", "tone": "warm", "occasion": "通勤/温柔",
     "desc": "温柔豆沙粉，日常百搭"},
    {"hex": "CD5C5C", "name": "珊瑚红", "tone": "warm", "occasion": "春夏/活力",
     "desc": "珊瑚色，活泼显气色"},
    {"hex": "AD1457", "name": "车厘子", "tone": "cool", "occasion": "秋冬/复古",
     "desc": "深车厘子红，浓郁显白"},
    {"hex": "E0115F", "name": "桃红", "tone": "cool", "occasion": "派对/亮眼",
     "desc": "亮桃红，张扬有活力"},
    {"hex": "722F37", "name": "干枯玫瑰", "tone": "cool", "occasion": "通勤/温柔",
     "desc": "干枯玫瑰色，低调温柔"},
    {"hex": "C71585", "name": "紫红", "tone": "cool", "occasion": "舞台/个性",
     "desc": "紫调口红，个性十足"},
    {"hex": "FF4040", "name": "炽热红", "tone": "warm", "occasion": "舞台/亮眼",
     "desc": "高饱和亮红，吸睛"},
    {"hex": "960018", "name": "胭脂红", "tone": "warm", "occasion": "复古/浓郁",
     "desc": "深胭脂红，有韵味"},
    {"hex": "DA70D6", "name": "樱花粉", "tone": "cool", "occasion": "少女/日常",
     "desc": "樱花粉，甜美清透"},
    {"hex": "800000", "name": "枫叶红", "tone": "warm", "occasion": "秋冬/气质",
     "desc": "深枫叶红，沉稳显白"},
    {"hex": "FF69B4", "name": "芭比粉", "tone": "cool", "occasion": "少女/潮流",
     "desc": "芭比粉，甜酷风"},
    {"hex": "9C2542", "name": "石榴红", "tone": "cool", "occasion": "宴会/复古",
     "desc": "石榴红，浓郁饱满"},
    {"hex": "E30B5D", "name": "莓果红", "tone": "cool", "occasion": "日常/活力",
     "desc": "莓果红，显白提气"},
]


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
    返回: [{"hex","name","tone","occasion","desc","dE"}, ...] 按色差升序
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
            print("  #%s %s  dE=%.2f  (%s)" % (r["hex"], r["name"], r["dE"], r["occasion"]))
