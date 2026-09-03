# -*- coding: utf-8 -*-
"""hue_test：测试3「色相渐变排列」——错误轴定位，与测试1 构成类型判定双证据链

设计（对应 project.md 6.9 三测试体系的"轴向"环节）：
    学术原型：Farnsworth-Munsell 100 Hue / D-15 排列测试（临床金标准）。
    简化数字化：N 个等色相间隔色块打乱呈现，用户拖拽排成"看起来平滑的渐变"。

    核心原理——错误轴（error axis）：
        正常视觉：排列基本正确，错误少且随机。
        色觉缺陷：在其混淆轴附近的色相区，色块"看起来"失去色相顺序
                  → 排列错误集中爆发在该色相区 → 错误的色相分布有明显主轴。
        红-绿缺陷（protan/deutan）→ 错误轴沿 CIELAB a* 轴（红 0° ≡ 绿 180°）
        蓝-黄缺陷（tritan）       → 错误轴沿 CIELAB b* 轴（黄 90° ≡ 蓝 270°）

    模拟用户模型（自动测试用）：
        用户看到的颜色 = simulate_cvd(色块, type, severity)
        排列策略 = 两端色块固定为锚（FM100 惯例），中间块按"看到的色相角"排序
        + noise_deg 随机抖动 = 人的非色觉误差（手抖/粗心），严重缺陷时
          混淆区色相坍缩 → 排序由噪声决定 → 错误集中爆发（与真实行为一致）。

    双倍角环形统计（为什么不是普通向量合成）：
        错误常同时出现在红(≈0°)与绿(≈180°)两个对径区，普通向量合成
        会互相抵消；把色相角乘 2 再做向量合成，对径区同轴同向叠加，
        得到"轴"而非"方向"（环形统计标准技巧，Fisher 1993）。

    判定分工（6.9 双证据链）：
        测试1（伪等色图）→ type 定性分型（deutan/protan/tritan）
        测试3（本模块）  → 错误轴独立佐证（red-green vs blue-yellow）
        两者一致 → 判定可信；矛盾 → 复测（诚实边界：不强行二选一）
"""
import math

import numpy as np

from .color_diff import _D65, _KAPPA, _M_XYZ2RGB, ciede2000, lab2srgb, srgb2lab
from .cvd_matrix import simulate_cvd

# 轴向判定常量（CIELAB 色相角，轴是双向的：0°≡180°）
AXIS_REDGREEN = 0.0    # a* 轴：红(0°) ≡ 绿(180°)
AXIS_BLUEYELLOW = 90.0  # b* 轴：黄(90°) ≡ 蓝(270°)


def _lab_in_gamut(lab):
    """Lab 是否在 sRGB 色域内（反解线性 RGB 不越界 [0,1]）

    为什么不用"往返检测"？clip 色的往返也稳定（都压到同一边界），
    往返差≈0 无法暴露越界——必须检查反解的线性 RGB 本身。
    """
    lab = np.asarray(lab, dtype=np.float64)
    L, a, b = lab
    fy = (L + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0
    d = 6.0 / 29.0
    finv = lambda f: f ** 3 if f > d else (116.0 * f - 16.0) / _KAPPA
    xyz = np.array([finv(fx), finv(fy), finv(fz)]) * _D65
    lin = xyz @ _M_XYZ2RGB.T
    return bool(np.all(lin >= -1e-9) and np.all(lin <= 1.0 + 1e-9))


def make_hue_sequence(n=15, L=62.0, C=28.0, h_start=0.0, h_end=360.0):
    """生成等色相间隔的渐变色块序列（sRGB）

    关键：高饱和的蓝紫/绿黄区可能超出 sRGB 色域 → 二分压彩度
    （保持该块色相角与明度不变，只降 C*，保证序列仍按色相均匀递进）。

    参数：
        n               色块数（15 与 D-15 量级一致，全环 24°/块）
        L               统一明度（消除明度线索，逼用户只用色相）
        C               目标彩度（越界自动降低）
        h_start/h_end   色相范围（默认全环，endpoint=False 不重复首块）
    返回：
        rgbs    (n,3) uint8
        hues    (n,) float 各块真实色相角（评分/轴定位用）
        c_used  (n,) float 实际采用的彩度（越界块被压低）
    """
    hues = np.linspace(h_start, h_end, n, endpoint=False) % 360.0
    rgbs, c_used = [], []
    for hd in hues:
        rad = math.radians(hd)
        lab_of = lambda c: np.array([L, c * math.cos(rad), c * math.sin(rad)])
        if _lab_in_gamut(lab_of(C)):
            c_use = C
        else:
            lo, hi = 0.0, C
            for _ in range(32):
                mid = (lo + hi) / 2.0
                if _lab_in_gamut(lab_of(mid)):
                    lo = mid
                else:
                    hi = mid
            c_use = lo * 0.995  # 留 0.5% 余量，防 round 后触界
        rgbs.append(lab2srgb(lab_of(c_use)))
        c_used.append(c_use)
    return np.array(rgbs), hues, np.array(c_used)


def shuffle_order(n, seed=None):
    """打乱色块呈现顺序（出题用；0 号块固定第一 = UI 参考锚）"""
    rng = np.random.default_rng(seed)
    disp = np.arange(n)
    if n > 1:
        rest = rng.permutation(np.arange(1, n))
        disp = np.concatenate([[0], rest])
    return disp


JND_ARRANGE = 2.0  # 排列任务分辨阈（ΔE00）：分不出 → 随机放
# 为什么 2.0 高于并排辨色 JND（≈1.5）？排列任务靠"记忆+顺序比较"，
# 心理物理学上分辨阈高于并排对照（FM100 文献量级）；上线前用真人数据校准。


def _cluster_shuffle(idx_sorted, sim_labs, jnd=JND_ARRANGE, rng=None):
    """把"感知上分不出顺序"的相邻块群内随机洗牌（模拟真实用户行为）

    用户按看到的色相排序，但相邻块模拟色 ΔE00 < JND 时他分不出谁先谁后
    → 实际行为是随机放。缺陷越重 → 混淆区坍缩越狠 → 群越大 → 错误越多。
    """
    rng = np.random.default_rng(rng)
    out = np.asarray(idx_sorted).copy()
    if len(out) < 2:
        return out
    des = ciede2000(sim_labs[out[:-1]], sim_labs[out[1:]])
    i = 0
    while i < len(out):
        j = i
        while j < len(out) - 1 and des[j] < jnd:   # des[k] = out[k] 与 out[k+1] 的色差
            j += 1
        if j > i:
            out[i:j + 1] = rng.permutation(out[i:j + 1])
        i = j + 1
    return out


def simulate_arrangement(rgbs, kind="deutan", severity=1.0, noise_deg=3.0,
                         rng=None, anchor="both"):
    """模拟用户在"色相排列"任务中的行为（自动测试/阈值校准用）

    模型（三层，逐步逼近真实行为）：
        ① 看到的颜色 = simulate_cvd(色块)
        ② 以两端色块为锚（FM100 惯例），中间块按"看到的色相角"排序
        ③ 相邻块模拟色 ΔE00 < JND_ARRANGE → 群内随机（分不出 → 随机放）
        + noise_deg 手部抖动 = 非色觉误差

    参数：
        rgbs       (n,3) 色块真实颜色（按正确顺序给出）
        kind/severity  用户的缺陷类型与程度
        noise_deg  排序角抖动（正常人也有）
        anchor     "both"（两端锚定）/ "first"（仅首块锚定）/ "none"
    返回：
        order  (n,) int，order[k] = 用户放在位置 k 的色块（原始索引）
    """
    rng = np.random.default_rng(rng)
    rgbs = np.asarray(rgbs, dtype=np.float64)
    n = len(rgbs)
    sim = simulate_cvd(rgbs, kind, severity).astype(np.float64)
    lab = srgb2lab(sim)
    h = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360.0

    if anchor == "both" and n >= 3:
        mid = np.arange(1, n - 1)
        rel = (h[mid] - h[0]) % 360.0
        if noise_deg > 0:
            rel = (rel + rng.uniform(-noise_deg, noise_deg, mid.size)) % 360.0
        mid_sorted = mid[np.argsort(rel, kind="stable")]
        mid_sorted = _cluster_shuffle(mid_sorted, lab, JND_ARRANGE, rng)
        order = np.concatenate([[0], mid_sorted, [n - 1]])
    elif anchor == "first" and n >= 2:
        idx = np.arange(1, n)
        rel = (h[idx] - h[0]) % 360.0
        if noise_deg > 0:
            rel = (rel + rng.uniform(-noise_deg, noise_deg, idx.size)) % 360.0
        mid_sorted = idx[np.argsort(rel, kind="stable")]
        mid_sorted = _cluster_shuffle(mid_sorted, lab, JND_ARRANGE, rng)
        order = np.concatenate([[0], mid_sorted])
    else:
        rel = h + (rng.uniform(-noise_deg, noise_deg, n) if noise_deg > 0 else 0.0)
        order = np.argsort(rel % 360.0, kind="stable")
        order = _cluster_shuffle(order, lab, JND_ARRANGE, rng)
    return order


def arrangement_error(order):
    """FM100 风格总错误分：Σ|用户位置 - 正确位置|

    完美排列 = 0；正常人（有噪声）个位数；明显缺陷几十以上（n=15 时）。
    """
    order = np.asarray(order)
    return int(np.abs(np.arange(len(order)) - order).sum())


def error_by_block(order):
    """每个色块的错位量 |pos - block|（轴定位的原料）"""
    order = np.asarray(order)
    return np.abs(np.arange(len(order)) - order).astype(np.float64)


def detect_confusion_pairs(order, rgbs, exp_step=None, tol_frac=0.5):
    """找出用户排列中的"混淆对"——被放成相邻、但真实色相间隔显著偏离期望的块对

    为什么统计"对"而不是"错位块"？
        FM100/Vingrys-King-Smith 临床方法：缺陷用户把"他看来相近"的块
        放在一起，而这些块对的真实色差方向恰好沿其混淆轴
        （deutan 把红绿放一起 → 该对真实色差 ≈ a* 轴）。
        统计"错位块的色相"会被"坍缩区整体乱序"污染（错误覆盖宽区间），
        统计"对"才能锁定混淆方向。

    参数：
        order     用户排列（order[k] = 位置 k 的块）
        rgbs      色块真实颜色（按正确顺序）
        exp_step  期望相邻色相间隔（默认 360/n，全环假设）
        tol_frac  间隔偏离超过 exp_step*tol_frac 记为混淆对
    返回：
        pairs  [{"pos", "i", "j", "err", "vec"(da,db)}...]，vec = 两块真实 Lab 色差
    """
    labs = srgb2lab(np.asarray(rgbs, dtype=np.float64))
    order = np.asarray(order, dtype=int)
    n = len(order)
    if exp_step is None:
        exp_step = 360.0 / n
    h = np.degrees(np.arctan2(labs[:, 2], labs[:, 1])) % 360.0
    pairs = []
    for k in range(n - 1):
        i, j = int(order[k]), int(order[k + 1])
        dh = abs((h[j] - h[i] + 180.0) % 360.0 - 180.0)   # 环向最短间隔
        err = abs(dh - exp_step)
        if err > tol_frac * exp_step:
            pairs.append({
                "pos": k, "i": i, "j": j, "err": float(err),
                "vec": (float(labs[j, 1] - labs[i, 1]),
                        float(labs[j, 2] - labs[i, 2])),
            })
    return pairs


def error_axis(order, rgbs, exp_step=None, tol_frac=0.5, n_bins=12):
    """混淆对的真实色差方向 → 双倍角合成 → 混淆轴（FM100 正统统计量）

    为什么双倍角？deutan 的混淆对（红-绿、橙-黄绿…）的 Lab 色差向量
    方向分布在 135°~180° 一带，普通合成对"对径翻转"敏感；
    2θ 合成使 -20° 与 160° 同轴叠加，得到稳定"轴"而非"方向"
    （环形统计标准技巧，Fisher 1993；Vingrys & King-Smith 1988）。

    参数：
        order/rgbs/exp_step/tol_frac  同 detect_confusion_pairs
    返回：
        axis_deg    混淆轴 ∈ [0,180)：0°≡红绿轴(a*)，90°≡蓝黄轴(b*)
        strength    轴显著度 = 合成向量长度 / Σ权重（0~1，越大越集中）
        pairs       混淆对明细（诊断/落盘用）
    """
    pairs = detect_confusion_pairs(order, rgbs, exp_step, tol_frac)
    if not pairs:
        return 0.0, 0.0, pairs
    w = np.array([p["err"] for p in pairs])
    ang2 = np.radians([2.0 * math.degrees(math.atan2(p["vec"][1], p["vec"][0]))
                       for p in pairs])
    sx = float(w @ np.cos(ang2))
    sy = float(w @ np.sin(ang2))
    total = float(w.sum())
    strength = math.hypot(sx, sy) / total          # 归一化显著度 ∈ [0,1]
    axis = math.degrees(math.atan2(sy, sx) / 2.0) % 180.0
    return axis, strength, pairs


def _axis_dist(deg, axis_deg):
    """角到"轴"的最小距离（轴双向：0°≡180°）"""
    d = abs((deg - axis_deg) % 180.0)
    return min(d, 180.0 - d)


def infer_deficit_axis(total_error, axis_deg, strength,
                       err_clear=5.0, margin=15.0, strength_min=0.45):
    """错误分 + 混淆轴 → 轴级判定（类型判定第二证据）

    参数：
        err_clear    总错误分低于此 → normal。模拟语境下正常用户 err≈0
                     （真实人的粗心/年龄错误由 strength 门兜底：方向随机
                     → 显著度低 → unclear，不会误判为某类缺陷）
        margin       两轴距离差超过此才下结论（避免边界摇摆）
        strength_min 轴显著度（0~1）低于此 → 混淆对方向分散、不可判轴
    返回：
        verdict  "normal" / "red-green" / "blue-yellow" / "unclear"
        detail   {axis, d_redgreen, d_blueyellow, strength, n_pairs}
    """
    detail = {"axis": round(axis_deg, 1), "strength": round(strength, 2),
              "d_redgreen": round(_axis_dist(axis_deg, AXIS_REDGREEN), 1),
              "d_blueyellow": round(_axis_dist(axis_deg, AXIS_BLUEYELLOW), 1)}
    if total_error < err_clear:
        return "normal", detail
    if strength < strength_min:
        return "unclear", detail
    d_rg = _axis_dist(axis_deg, AXIS_REDGREEN)
    d_by = _axis_dist(axis_deg, AXIS_BLUEYELLOW)
    if d_rg + margin <= d_by:
        return "red-green", detail
    if d_by + margin <= d_rg:
        return "blue-yellow", detail
    return "unclear", detail


def judge_arrangement(user_order, rgbs, exp_step=None, err_clear=5.0, margin=15.0):
    """用户排列结果 → 评分卡（测试3 主接口，UI 层只调这个）

    返回 dict：total_error / axis_deg / axis_strength / verdict / detail / n_pairs
    """
    total = arrangement_error(user_order)
    axis, strength, pairs = error_axis(user_order, rgbs, exp_step)
    verdict, detail = infer_deficit_axis(total, axis, strength, err_clear, margin)
    detail["n_pairs"] = len(pairs)
    return {
        "total_error": total,
        "axis_deg": detail["axis"],
        "axis_strength": detail["strength"],
        "verdict": verdict,
        "detail": detail,
        "pairs": pairs,
    }


def save_strip(rgbs, order, path, cell_w=34, height=64):
    """按 order 画单行色带（order[k]=位置 k 放的块；0~255 RGB）"""
    rgbs = np.asarray(rgbs, dtype=np.uint8)
    order = np.asarray(order, dtype=int)
    n = len(order)
    img = np.zeros((height, n * cell_w, 3), dtype=np.uint8)
    for k, blk in enumerate(order):
        img[:, k * cell_w:(k + 1) * cell_w] = rgbs[blk]
    return img


def save_compare(rgbs, order_user, path, cell_w=34, height=64, gap=12):
    """上图=正确顺序（他人视角） / 下图=用户排列 → 错位一目了然，落盘供答辩展示"""
    from .grid_test import save_grid
    top = save_strip(rgbs, np.arange(len(rgbs)), None, cell_w, height)
    bottom = save_strip(rgbs, order_user, None, cell_w, height)
    h, w = top.shape[:2]
    canvas = np.full((2 * h + gap, w, 3), 245, dtype=np.uint8)
    canvas[:h] = top
    canvas[h + gap:] = bottom
    save_grid(canvas, path)
    return canvas
