# -*- coding: utf-8 -*-
"""cvd_matrix：CVD 模拟与混淆方向（Machado et al. 2009 模型）

为什么需要它？（测试1 伪等色图 / 双视角自我渲染 / 个性化校色 共同的数学前提）
    给定色觉缺陷类型与严重度，计算"该用户看任意颜色时的等效颜色"。
    模拟模型的科学依据：Viénot 1999 真人实验——模拟图经红绿色盲本人确认
    与其真实观感一致（详见答辩话术库金句4）。

模型选择：Machado 2009（优于 Viénot/Brettel 的点）
    ① 自带严重度参数 severity（0=正常 → 1=完全双色视），与 6.9 个人档案直接对接
    ② 严格作用于【线性 RGB】空间（sRGB → 线性 → 矩阵 → sRGB）

核心数学（测试1 的灵魂）：
    模拟矩阵 M 的【零空间方向】= 该缺陷"完全看不见"的颜色变化方向：
        颜色差 d 经 M 后消失 ⟺ d @ M.T = 0 ⟺ d ∈ null(M)
    沿零空间方向偏移构造混淆色对 → 色盲模拟后严格相同（不可分），
    正常视觉差异显著（可分）——这就是伪等色图"数字隐身"的构造原理。
    severity < 1 时矩阵可逆（无精确零空间），取最小奇异值方向作为
    "最不可见方向"（近似混淆方向），残差随 severity 降低而增大——
    这天然实现了"程度越轻，混淆越弱"的连续过渡。

包含：
    simulate_cvd        模拟色觉缺陷视角（severity 可调）
    confusion_direction 该缺陷下"最不可见"的颜色变化方向
    confusion_pair      构造混淆色对（伪等色图的原材料）
"""
import numpy as np

from .color_diff import lab2srgb, srgb2lab

# Machado 2009 完全型模拟矩阵（severity = 1.0），作用于线性 RGB
# 每行和 ≈ 1 → 灰轴（R=G=B）不动：色盲用户的明度感知被正确保留
_M_FULL = {
    "protan": np.array([           # 红色盲（L 视锥缺失）
        [0.152286, 1.052583, -0.204868],
        [0.114503, 0.786281, 0.099216],
        [-0.003882, -0.048116, 1.051998],
    ]),
    "deutan": np.array([           # 绿色盲（M 视锥缺失，最常见）
        [0.367322, 0.860646, -0.227968],
        [0.280085, 0.672501, 0.047413],
        [-0.011820, 0.042940, 0.968881],
    ]),
    "tritan": np.array([           # 蓝黄色盲（S 视锥缺失，罕见）
        [1.255528, -0.076749, -0.178779],
        [-0.078411, 0.930809, 0.147602],
        [0.004733, 0.691367, 0.303900],
    ]),
}

_CVD_KINDS = tuple(_M_FULL.keys())


def _effective_matrix(kind, severity):
    """有效模拟矩阵：identity 与完全型之间线性插值

    说明：Machado 原论文在 LMS 空间插值投影点，此处线性插值是工程近似
    （答辩口径：近似误差由 6.9 真人测评校准弥补，见答辩话术库诚实边界）。
    """
    if kind not in _M_FULL:
        raise ValueError(f"未知色觉缺陷类型: {kind}，可选 {_CVD_KINDS}")
    s = float(np.clip(severity, 0.0, 1.0))
    return (1.0 - s) * np.eye(3) + s * _M_FULL[kind]


def simulate_cvd(rgb, kind="deutan", severity=1.0):
    """模拟色觉缺陷视角

    参数：
        rgb      (...,3) uint8/float，sRGB 0~255
        kind     "protan" / "deutan" / "tritan"
        severity 0.0（正常）~ 1.0（完全双色视）
    返回：
        (...,3) uint8，该用户眼中的等效颜色
    """
    from .color_diff import _linear_to_srgb, _srgb_to_linear  # 复用 gamma 函数
    rgb = np.asarray(rgb, dtype=np.float64)
    lin = _srgb_to_linear(rgb)
    mat = _effective_matrix(kind, severity)
    sim_lin = lin @ mat.T                      # 行向量约定：y = x @ M.T
    return _linear_to_srgb(sim_lin).round().astype(np.uint8)


def confusion_direction(kind, severity=1.0):
    """该缺陷下"最不可见"的颜色变化方向（【线性 RGB 空间】，归一化到 ±1）

    数学：severity=1 时 deutan/protan 矩阵有精确零空间（最小奇异值≈0），
          方向 = 最小奇异值对应的右奇异向量；
          tritan 矩阵（Machado 原文）是近似投影，方向为"变化最不易察觉"方向；
          severity<1 时零空间不存在，同理取最小奇异值方向。
    用途：伪等色图混淆色对的偏移轴（ishihara.py）。
    """
    mat = _effective_matrix(kind, severity)
    _u, s, vt = np.linalg.svd(mat)
    d = vt[-1]                                 # 最小奇异值对应的右奇异向量
    d = d / np.max(np.abs(d))                  # 尺度归一（分量 ≤1，便于步长控制）
    return d


def confusion_pair(base_rgb, kind, severity=1.0, step=0.12):
    """构造混淆色对 (rgb_a, rgb_b)

    关键：偏移必须发生在【线性 RGB 空间】——Machado 矩阵作用于线性域，
    零空间结构只在线性域成立；若在 sRGB（gamma 编码）空间偏移，
    gamma 非线性会破坏等色性（模拟后残差可达 ΔE≈2，且随位置漂移）。

    参数：
        base_rgb  sRGB 0~255
        step      【线性域】偏移步长（0.05~0.2 量级；正常域 ΔE 由此自适应）
    返回：
        (rgb_a, rgb_b, dE_normal, dE_sim)——后两者供自适应与测试断言
        severity=1（deutan/protan）时 dE_sim 仅剩 uint8 量化残差（<1.5）
    """
    from .color_diff import _linear_to_srgb, _srgb_to_linear
    base = np.asarray(base_rgb, dtype=np.float64)
    d = confusion_direction(kind, severity)          # 线性空间方向
    base_lin = _srgb_to_linear(base)
    lin_a = np.clip(base_lin - step * d / 2.0, 0.0, 1.0)
    lin_b = np.clip(base_lin + step * d / 2.0, 0.0, 1.0)
    rgb_a = _linear_to_srgb(lin_a)                   # 0~255 float
    rgb_b = _linear_to_srgb(lin_b)
    lab_a, lab_b = srgb2lab(rgb_a), srgb2lab(rgb_b)
    sim_a = srgb2lab(simulate_cvd(rgb_a, kind, severity))
    sim_b = srgb2lab(simulate_cvd(rgb_b, kind, severity))
    from .color_diff import ciede2000
    return rgb_a, rgb_b, float(ciede2000(lab_a, lab_b)), float(ciede2000(sim_a, sim_b))
