# -*- coding: utf-8 -*-
"""grid_test：测试2「网格找异色块」——定量测 ΔL/ΔC/ΔH 分辨阈值（project.md 6.9）

设计（对应 6.9 三测试体系的"定量"环节）：
    N×N 网格同色块 + 1 个异色块，用户指出位置。
    阶梯法（staircase，1-up/1-down）：
        答对 → 下一轮差异更小；答错 → 放宽一档。
        记录"反转点"（对↔错的切换处），反转点均值 = 分辨阈值
        （收敛于 ~50% 正确率，即"恰可察觉差 JND"的合理近似）。

三维度严格分开测（6.9 铁律：混在一张网格 = 测出混合阈值，不科学）：
    DIM_L  明度维 : 只改 L*（ΔL*，a/b 不动）
    DIM_C  彩度维 : 只改 C*（ΔC*，色相角不动）
    DIM_H  色相维 : 只改 h°（Δh，C* 不动）

学术原型：FM-100 排列测试 / Farnsworth D-15 的数字化变体（论证背书）。
边界说明：8bit sRGB 显示的最小可表达差异有限（最细几级 RGB 可能相同），
    用户必然答错 → 阶梯自动放宽 → 天然收敛到"该屏幕可测的下限"，无需特殊处理。
"""
import math

import numpy as np

from .color_diff import ciede2000, lab2srgb

# 三个测评维度（对外常量，接口按名字分类）
DIM_L = "L"   # 明度
DIM_C = "C"   # 彩度（饱和度）
DIM_H = "H"   # 色相

# 阈值阶梯（CIE 标准单位，index 0 最易 → 末尾最难）
# 数值为工程起点（基于 D-15/FM-100 临床量级 + 经验），上线前用真人数据校准。
# 答辩口径：阶梯法是心理物理学标准做法 + 校准计划 = 评测体系的一部分。
LEVELS = {
    DIM_L: [12.0, 8.0, 5.5, 4.0, 3.0, 2.2, 1.6, 1.2],     # ΔL*
    DIM_C: [16.0, 11.0, 8.0, 5.5, 4.0, 3.0, 2.2, 1.6],    # ΔC*
    DIM_H: [30.0, 20.0, 14.0, 10.0, 7.0, 5.0, 3.5, 2.5],  # Δh（度）
}


def _lch2lab(L, C, h_deg):
    """LCh(L*,C*,h°) → Lab"""
    h = math.radians(h_deg)
    return np.array([L, C * math.cos(h), C * math.sin(h)])


def _rand_base_lab(rng):
    """随机 base 色：中明度(L*45~70)、中彩度(C*22~45)、色相随机

    为什么限制范围？
        太暗/太亮/太灰的 base 会让阈值失真（Weber 对比度依赖背景亮度），
        C* 下限 22 保证 ΔC 负方向最大档(16)不会把彩度压到 0 附近。
    """
    L = rng.uniform(45.0, 70.0)
    C = rng.uniform(22.0, 45.0)
    h = rng.uniform(0.0, 360.0)
    return _lch2lab(L, C, h)


def _shift(lab, dim, delta, sign):
    """把 lab 沿指定维度偏移 delta（sign=±1，方向随机防用户找规律）

    越界保护：L* 限 [15,90]、C* 下限 5（base 范围已保证正常不触发，
    保护只为防御未来调参时引入静默失真）。
    """
    L, a, b = lab
    if dim == DIM_L:
        return np.array([np.clip(L + sign * delta, 15.0, 90.0), a, b])
    C = math.hypot(a, b)
    h = math.atan2(b, a)
    if dim == DIM_C:
        C2 = max(C + sign * delta, 5.0)
    else:  # DIM_H：C* 不变，色相角旋转
        h = h + sign * math.radians(delta)
        C2 = C
    return np.array([L, C2 * math.cos(h), C2 * math.sin(h)])


def make_round(dim, delta, n=4, cell=90, gap=6, bg=248, rng=None):
    """生成一轮"找异色块"网格图

    参数：
        dim    DIM_L / DIM_C / DIM_H
        delta  本轮差异量（CIE 单位：ΔL* / ΔC* / Δh°）
        n      每边格数（4 → 16 选 1）
        cell   单格边长(px)；gap 格间距(px)；bg 背景灰度
        rng    numpy Generator（传种子可复现）
    返回：
        img    (uint8, H×W×3, RGB) 网格图
        info   dict：odd 位置/两色 Lab/ΔE00（测试与日志用）
    """
    if rng is None:
        rng = np.random.default_rng()
    base = _rand_base_lab(rng)
    sign = 1 if rng.random() < 0.5 else -1
    odd = _shift(base, dim, delta, sign)
    odd_pos = (int(rng.integers(n)), int(rng.integers(n)))  # (row, col)

    base_rgb = lab2srgb(base)
    odd_rgb = lab2srgb(odd)

    size = n * cell + (n + 1) * gap
    img = np.full((size, size, 3), bg, dtype=np.uint8)
    for r in range(n):
        for c in range(n):
            y = gap + r * (cell + gap)
            x = gap + c * (cell + gap)
            img[y:y + cell, x:x + cell] = odd_rgb if (r, c) == odd_pos else base_rgb

    info = {
        "dim": dim, "delta": float(delta), "odd_pos": odd_pos, "n": n,
        "base_lab": base.round(2).tolist(), "odd_lab": odd.round(2).tolist(),
        "deltaE00": float(ciede2000(base, odd)),
    }
    return img, info


class ThresholdRunner:
    """单维度阶梯法测阈值（1-up/1-down 简化版）

    流程：next_round() 出图 → 用户 submit(pos) → 自动升降级 → done 后 threshold()
    阈值估计：反转点（对↔错切换轮）的 delta 均值；全程无反转时取末轮 delta
    （无反转 = 用户远强/远弱于量程两端，末轮 delta 即合理估计）
    """

    def __init__(self, dim, start_level=1, n_reversals=4, max_rounds=12, seed=None):
        self.dim = dim
        self.levels = LEVELS[dim]
        self.level = min(max(start_level, 0), len(self.levels) - 1)
        self.n_reversals = n_reversals
        self.max_rounds = max_rounds
        self.rng = np.random.default_rng(seed)
        self.last_correct = None
        self.reversal_deltas = []
        self.history = []          # [(round, delta, correct), ...]
        self.done = False
        self._info = None

    def current_delta(self):
        return self.levels[self.level]

    def next_round(self, **kw):
        """生成下一轮网格。返回 (img, info)"""
        self._img, self._info = make_round(self.dim, self.current_delta(), rng=self.rng, **kw)
        return self._img, self._info

    def submit(self, pos):
        """提交本轮答案 pos=(row,col)。返回 dict(done/correct/level/delta)"""
        if self._info is None:
            raise RuntimeError("先调用 next_round() 再 submit()")
        correct = tuple(pos) == tuple(self._info["odd_pos"])
        self.history.append((len(self.history) + 1, self.current_delta(), correct))

        # 反转检测：与上一轮对错相反 → 记录本轮 delta（推进前的值）
        if self.last_correct is not None and self.last_correct != correct:
            self.reversal_deltas.append(self.current_delta())
        self.last_correct = correct

        # 阶梯推进：答对升级（更难），答错降级（更易），两端截断
        self.level = max(0, min(self.level + (1 if correct else -1), len(self.levels) - 1))

        if len(self.reversal_deltas) >= self.n_reversals or len(self.history) >= self.max_rounds:
            self.done = True
        return {"done": self.done, "correct": correct,
                "level": self.level + 1, "delta": self.current_delta()}

    def threshold(self):
        """该维度分辨阈值估计（CIE 单位）"""
        if self.reversal_deltas:
            return float(np.mean(self.reversal_deltas))
        if self.history:
            return self.history[-1][1]
        return None


def _wrong_pos(info, rng):
    """随机挑一个非 odd 的位置（模拟用户答错时的"猜测"）"""
    n = info["n"]
    while True:
        pos = (int(rng.integers(n)), int(rng.integers(n)))
        if pos != tuple(info["odd_pos"]):
            return pos


def simulate_user(runner, true_delta, p_correct=0.9):
    """模拟"真实分辨阈值为 true_delta"的虚拟用户，把 runner 跑完（自动测试用）

    阈值语义：true_delta = 恰可察觉差 JND —— 差异 >= JND 才看得见。
    规则：当前轮 delta >= true_delta 视为"看得见"（以 p_correct 概率答对），
    否则以 (1-p_correct) 概率蒙对（略高于 1/n² 的纯猜测，保守估计）。
    """
    while not runner.done:
        _, info = runner.next_round()
        can_see = info["delta"] >= true_delta
        hit = runner.rng.random() < (p_correct if can_see else 1.0 - p_correct)
        runner.submit(info["odd_pos"] if hit else _wrong_pos(info, runner.rng))
    return runner


def build_profile(results):
    """三维度结果 → UserColorProfile 的阈值部分（6.9 定义的档案结构）

    参数：results 形如 {DIM_L: runner, DIM_C: runner, DIM_H: runner}
    返回：{"dL_threshold": .., "dC_threshold": .., "dH_threshold": ..}
    说明：cvd_type/severity 由测试1（伪等色图）+测试3（排列轴向）判定，
          本函数只负责测试2 的三个定量阈值 —— 职责单一。
    """
    return {
        "dL_threshold": results[DIM_L].threshold(),
        "dC_threshold": results[DIM_C].threshold(),
        "dH_threshold": results[DIM_H].threshold(),
    }


def save_grid(img, path):
    """网格图落盘（imencode 方案，规避 cv2.imwrite 中文路径问题；只依赖 cv2，
    不 import beauty.common —— 避免测评模块被 torch 拖累加载）"""
    import cv2
    ext = "." + path.rsplit(".", 1)[-1].lower()
    params = [int(cv2.IMWRITE_JPEG_QUALITY), 95] if ext in (".jpg", ".jpeg") else []
    ok, buf = cv2.imencode(ext, cv2.cvtColor(img, cv2.COLOR_RGB2BGR), params)
    if not ok:
        raise RuntimeError("imencode 失败: " + path)
    with open(path, "wb") as f:
        f.write(buf.tobytes())
