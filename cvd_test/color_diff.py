# -*- coding: utf-8 -*-
"""color_diff：CIE 标准色彩空间与色差计算（纯 numpy，零重依赖）

为什么自己实现而不用第三方库？
    色觉测评（ΔL/ΔC/ΔH 阈值）和色号检索（CIEDE2000）都建立在
    "标准 Lab 空间 + 标准色差公式"上。第三方库（colormath 等）依赖重，
    而本项目只需要这几个函数 → 按 CIE 标准公式用 numpy 自实现，
    公式依据 Sharma et al. 2005（CIEDE2000 官方实现要点）。

包含：
    srgb2lab    sRGB(0~255) → CIELAB（D65 白点）
    lab2srgb    CIELAB → sRGB（越界 clip 到色域边缘）
    ciede2000   CIEDE2000 色差 ΔE00（美妆/纺织行业标准色差公式）
"""
import numpy as np

# D65 白点（2° 视场标准观察者）
_D65 = np.array([0.95047, 1.00000, 1.08883])
# sRGB(D65) 线性 RGB → XYZ 变换矩阵
_M_RGB2XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])
_M_XYZ2RGB = np.linalg.inv(_M_RGB2XYZ)
# CIE 标准常数
_EPS = 216.0 / 24389.0     # ≈0.008856，线性/非线性分段点
_KAPPA = 24389.0 / 27.0    # ≈903.3


def _srgb_to_linear(c):
    """sRGB gamma 展开：0~255 → 线性光 0~1"""
    c = np.asarray(c, dtype=np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(c):
    """线性光 0~1 → sRGB 0~255（负值 clip 掉，来自 Lab 越界反解）"""
    c = np.asarray(c, dtype=np.float64)
    c = np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.clip(c, 0.0, None), 1 / 2.4) - 0.055)
    return np.clip(c * 255.0, 0, 255)


def srgb2lab(rgb):
    """sRGB → CIELAB

    参数：rgb 形状 (...,3)，0~255
    返回：(...,3) float64，(L*, a*, b*)，L*∈[0,100]
    """
    lin = _srgb_to_linear(rgb)
    xyz = lin @ _M_RGB2XYZ.T
    t = xyz / _D65
    f = np.where(t > _EPS, np.cbrt(t), (_KAPPA * t + 16.0) / 116.0)
    L = 116.0 * f[..., 1] - 16.0
    a = 500.0 * (f[..., 0] - f[..., 1])
    b = 200.0 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def lab2srgb(lab):
    """CIELAB → sRGB

    参数：lab 形状 (...,3)
    返回：(...,3) uint8（Lab 越界部分 clip 到 sRGB 色域边缘）
    """
    lab = np.asarray(lab, dtype=np.float64)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0
    d = 6.0 / 29.0

    def _finv(f):
        """f 的逆：非线性段 f³，线性段 (116f-16)/κ"""
        return np.where(f > d, f ** 3, (116.0 * f - 16.0) / _KAPPA)

    xyz = np.stack([_finv(fx), _finv(fy), _finv(fz)], axis=-1) * _D65
    # 注意行向量约定：正向是 lin @ M.T，反向对应 xyz @ M⁻¹.T（漏 .T 会静默失真）
    lin = xyz @ _M_XYZ2RGB.T
    return _linear_to_srgb(lin).round().astype(np.uint8)


def ciede2000(lab1, lab2):
    """CIEDE2000 色差 ΔE00

    参数：lab1/lab2 形状 (...,3)，可广播
    返回：ΔE00（标量或数组）

    为什么用 ΔE00 而不是 ΔE76（欧氏距离）？
        ΔE76 在蓝色区严重高估感知差异；ΔE00 加了亮度/彩度/色相
        三重加权修正，是美妆行业（口红"色差 ΔE<1 视为同色"）的
        通行标准 —— 对本项目"精确色彩计算下沉算法层"是基石。
    """
    lab1 = np.asarray(lab1, dtype=np.float64)
    lab2 = np.asarray(lab2, dtype=np.float64)
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]

    # 第 1 步：C_ab, Cbar, G 修正（修正 a* 轴的蓝色区问题）
    C1 = np.hypot(a1, b1)
    C2 = np.hypot(a2, b2)
    Cbar = (C1 + C2) / 2.0
    c7 = Cbar ** 7
    G = 0.5 * (1.0 - np.sqrt(c7 / (c7 + 25.0 ** 7)))
    a1p = (1.0 + G) * a1
    a2p = (1.0 + G) * a2
    C1p = np.hypot(a1p, b1)
    C2p = np.hypot(a2p, b2)

    # 第 2 步：色相角（atan2(0,0)=0 恰好符合 C1'=0 时 h'=0 的约定）
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0

    # 第 3 步：ΔL'、ΔC'、ΔH'
    dLp = L2 - L1
    dCp = C2p - C1p
    zeroC = (C1p * C2p) == 0
    dh = h2p - h1p
    dh = np.where(dh > 180.0, dh - 360.0, dh)
    dh = np.where(dh < -180.0, dh + 360.0, dh)
    dhp = np.where(zeroC, 0.0, dh)
    dHp = 2.0 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp) / 2.0)

    # 第 4 步：均值与加权函数
    Lbp = (L1 + L2) / 2.0
    Cbp = (C1p + C2p) / 2.0
    hsum = h1p + h2p
    habs = np.abs(h1p - h2p)
    hbp = np.where(
        zeroC, hsum,
        np.where(habs <= 180.0, hsum / 2.0,
                 np.where(hsum < 360.0, (hsum + 360.0) / 2.0,
                          (hsum - 360.0) / 2.0)))
    T = (1.0 - 0.17 * np.cos(np.radians(hbp - 30.0))
         + 0.24 * np.cos(np.radians(2.0 * hbp))
         + 0.32 * np.cos(np.radians(3.0 * hbp + 6.0))
         - 0.20 * np.cos(np.radians(4.0 * hbp - 63.0)))
    dtheta = 30.0 * np.exp(-(((hbp - 275.0) / 25.0) ** 2))
    cb7 = Cbp ** 7
    RC = 2.0 * np.sqrt(cb7 / (cb7 + 25.0 ** 7))
    SL = 1.0 + 0.015 * (Lbp - 50.0) ** 2 / np.sqrt(20.0 + (Lbp - 50.0) ** 2)
    SC = 1.0 + 0.045 * Cbp
    SH = 1.0 + 0.015 * Cbp * T
    RT = -np.sin(np.radians(2.0 * dtheta)) * RC

    return np.sqrt(
        (dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2
        + RT * (dCp / SC) * (dHp / SH))
