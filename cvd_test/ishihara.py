# -*- coding: utf-8 -*-
"""ishihara：测试1「伪等色图」——色盲类型定性判定（project.md 6.9）

原理（石原氏测试的数字化重实现，规避原版图卡版权）：
    利用"混淆色"（confusion colors）：某类色盲眼中看起来相同的颜色对。
    数字圆点用混淆色 A，背景圆点用混淆色 B：
        正常视觉：A/B 色差大            → 看得见数字
        对应色盲：A/B 模拟后严格相同     → 数字"隐身"
    数学构造：A/B 沿 CVD 模拟矩阵的【零空间方向】偏移（见 cvd_matrix.py），
    deutan 与 protan 零空间方向不同 → 同一套生成器天然支持分型出题。

关键防作弊设计（真实石原图的精髓，机器生成必须复现）：
    A、B 两族圆点各自带【同分布明度抖动】——否则用户可沿明度轮廓"看"出数字，
    测的就不是色相分辨而是明度分辨了。

判定输出：单类型图"可见/不可见" + 多图组合 → 与测试3 错误轴交叉验证，
构成 6.9 定义的"类型判定双证据链"。

包含：
    make_plate        生成一张伪等色图（数字 + 缺陷类型 + 严重度）
    simulate_plate    输出"该缺陷用户眼中"的图（评委体验 / 自动验证用）
    region_contrast   数字区 vs 背景区的 ΔE00（自动判定"可见性"的量化指标）
    judge_answer      判定用户回答
"""
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .color_diff import ciede2000, lab2srgb, srgb2lab
from .cvd_matrix import confusion_pair, simulate_cvd

# Windows 常见粗体字体候选（画数字用，粗体边缘实心便于圆点填充）
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/msyhbd.ttc",
]


def _load_font(size):
    for p in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _digit_mask(digit, size, font_path=None):
    """数字 → 二值掩膜（True = 数字区域）。数字居中，面积约占画布 40%"""
    font = (ImageFont.truetype(font_path, int(size * 0.62)) if font_path
            else _load_font(int(size * 0.62)))
    img = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), str(digit), font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1]),
              str(digit), font=font, fill=255)
    return np.array(img) > 128


def _rand_base_rgb(rng):
    """石原风格底色：中明度(L*55~70)中彩度(C*25~40)的暖色（色相角 30~60° 橙区）

    选暖色区的原因：红绿混淆对主要分布在暖色区（红绿盲的重灾区），
    且中明度中彩度留有向两侧偏移的色域余量（降低 clip 出界概率）。
    """
    C = rng.uniform(25.0, 40.0)
    h = math.radians(rng.uniform(30.0, 60.0))
    lab = np.array([rng.uniform(55.0, 70.0), C * math.cos(h), C * math.sin(h)])
    return lab2srgb(lab).astype(np.float64)


def make_plate(digit, kind="deutan", severity=1.0, size=420, seed=None,
               font_path=None, dot_step=14, r_min=4, r_max=9):
    """生成一张伪等色图

    参数：
        digit     题目数字（如 8 / 5 / 3）
        kind      混淆轴向 "deutan" / "protan" / "tritan"
        severity  严重度（1.0=完全双色视；<1 时数字隐身不完全，可用于测程度）
        size      画布边长(px)；dot_step 圆点栅格间距；r_min/r_max 点半径范围
        seed      随机种子（可复现）
    返回：
        img   (size,size,3) uint8 RGB
        info  {digit/kind/severity/step/rgb_a/rgb_b/dE_normal/dE_sim}
    """
    rng = np.random.default_rng(seed)
    mask = _digit_mask(digit, size, font_path)

    # 混淆对 + 自适应步长（线性域）：正常域 ΔE 至少 12（正常人轻松可辨），不够就加大步长
    base = _rand_base_rgb(rng)
    step = 0.12
    rgb_a, rgb_b, dE_n, dE_s = confusion_pair(base, kind, severity, step)
    for _ in range(8):
        if dE_n >= 12.0:
            break
        step *= 1.3
        rgb_a, rgb_b, dE_n, dE_s = confusion_pair(base, kind, severity, step)

    # 圆点填充：jittered grid + 【同分布】明度抖动与微噪声（防明度轮廓作弊）
    img = np.full((size, size, 3), 242, dtype=np.float64)
    gray = np.array([1.0, 1.0, 1.0])
    for gy in range(dot_step, size, dot_step):
        for gx in range(dot_step, size, dot_step):
            cx = int(gx + rng.uniform(-3, 3))
            cy = int(gy + rng.uniform(-3, 3))
            r = int(rng.uniform(r_min, r_max))
            j = rng.uniform(-7.0, 7.0)          # 明度抖动：两族共用同一分布
            noise = rng.uniform(-2.0, 2.0, 3)   # 微噪声：两族共用同一分布
            base_pt = rgb_a if mask[cy, cx] else rgb_b
            col = np.clip(base_pt + j * gray + noise, 0, 255).round().astype(int)
            cv2.circle(img, (cx, cy), r, col.tolist(), -1, lineType=cv2.LINE_AA)

    info = {
        "digit": str(digit), "kind": kind, "severity": severity, "step": step,
        "rgb_a": rgb_a.round(1).tolist(), "rgb_b": rgb_b.round(1).tolist(),
        "dE_normal": dE_n, "dE_sim": dE_s,
    }
    return img.round().astype(np.uint8), info


def simulate_plate(img, kind, severity=1.0):
    """输出"该缺陷用户眼中"的图——评委体验'数字隐身' / 自动验证用"""
    return simulate_cvd(img, kind, severity)


def region_contrast(img, mask):
    """数字区域 vs 背景区域的 ΔE00（各自均值色比较）

    用途：可见性的量化判据——
        正常视觉下 region_contrast 大  → 正常人看得见
        经 simulate 后 region_contrast 小 → 对应色盲看不见
    """
    lab = srgb2lab(img.astype(np.float64))
    num_mean = lab[mask].mean(axis=0)
    bg_mean = lab[~mask].mean(axis=0)
    return float(ciede2000(num_mean, bg_mean))


def judge_answer(ans, info):
    """判定用户回答

    返回：
        True  → 看出了数字（该轴向分辨正常）
        False → 看错/看不清（该轴向存在缺陷嫌疑，类型由多图+测试3 交叉确认）
    """
    return str(ans).strip() == str(info["digit"])
