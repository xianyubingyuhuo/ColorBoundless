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
from .cvd_matrix import confusion_direction, confusion_pair, simulate_cvd

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


def _rand_base_rgb(rng, kind="deutan"):
    """石原风格底色：中明度(L*55~70)中彩度(C*25~40)，色相区按混淆轴选（重灾区留偏移余量）

    deutan/protan（红绿轴）：暖色区（色相角 30~60° 橙区）——红绿混淆对的重灾区，
    中明度中彩度留有向两侧偏移的色域余量（降低 clip 出界概率）。
    tritan（蓝黄轴）：蓝黄混淆重灾区（黄绿区 75~105° / 蓝区 200~290° 随机二选一）——
    若沿用暖橙区，沿蓝黄零空间偏移的正常域 ΔE 很难达标（自适应步长放大也救不回）。
    """
    C = rng.uniform(25.0, 40.0)
    if kind == "tritan":
        h_deg = rng.uniform(75.0, 105.0) if rng.random() < 0.5 else rng.uniform(200.0, 290.0)
    else:
        h_deg = rng.uniform(30.0, 60.0)
    h = math.radians(h_deg)
    lab = np.array([rng.uniform(55.0, 70.0), C * math.cos(h), C * math.sin(h)])
    return lab2srgb(lab).astype(np.float64)


def _pair_by_dir(base_rgb, d, step, kind, severity):
    """confusion_pair 的方向参数化版（d 为线性域归一化方向）：供 tritan 方向精化扫描用"""
    from .color_diff import _linear_to_srgb, _srgb_to_linear
    base = np.asarray(base_rgb, dtype=np.float64)
    bl = _srgb_to_linear(base)
    la = np.clip(bl - step * np.asarray(d, float) / 2.0, 0.0, 1.0)
    lb = np.clip(bl + step * np.asarray(d, float) / 2.0, 0.0, 1.0)
    rgb_a, rgb_b = _linear_to_srgb(la), _linear_to_srgb(lb)
    lab_a, lab_b = srgb2lab(rgb_a), srgb2lab(rgb_b)
    sim_a = srgb2lab(simulate_cvd(rgb_a, kind, severity))
    sim_b = srgb2lab(simulate_cvd(rgb_b, kind, severity))
    return rgb_a, rgb_b, float(ciede2000(lab_a, lab_b)), float(ciede2000(sim_a, sim_b))


_DN_TARGET = 20.0   # 正常对比目标：deutan/protan 沿零空间方向 dE_s≈0，可拉到真板水平（20+）
_DN_FLOOR = 11.5    # 验收下限（tritan 物理受限 ≈12-13，以此为准）
_DS_CAP = 2.5       # 模拟域残差硬上限（tritan 物理下限 1.9-2.2，见 ROADMAP def 24）


def _pair_best(rng, kind, severity):
    """混淆对全局择优：48 base × 自适应步长，目标 = dE_s≤cap 下 dE_n 最大。

    对比旧版（dE_n≥11.5 即 break，48 次只取首个达标）：deutan/protan 沿零空间
    方向残差恒≈0（仅 uint8 量化），对比度可以拉到真板水平（20+）——正常视觉
    一眼可读；tritan 受 dE_s 物理上限主导，自适应停在 cap 附近（≈12-13）。
    择优键：达标者取 dE_n 最大；残差合规但欠对比者取 dE_n 最大；超 cap 者取残差最小。
    """
    best, best_key = None, None
    for _attempt in range(48):
        base = _rand_base_rgb(rng, kind)
        if kind == "tritan":
            d0 = np.asarray(confusion_direction(kind, severity), float)
            d0 = d0 / np.linalg.norm(d0)
            axis = np.eye(3)[int(np.argmin(np.abs(d0)))]
            u = np.cross(d0, axis); u /= np.linalg.norm(u)
            w = np.cross(d0, u)                 # {u,w} 张成 d0 的切平面 → α×θ 全方向覆盖
            dirs = [d0 * math.cos(al) + (u * math.cos(th) + w * math.sin(th)) * math.sin(al)
                    for al in np.linspace(0.0, math.pi / 2, 13)
                    for th in np.linspace(0.0, 2.0 * math.pi, 25, endpoint=False)]
            best_dir, best_ratio = None, 1e9
            for d in dirs:
                _, _, dn_p, ds_p = _pair_by_dir(base, d, 0.10, kind, severity)
                if dn_p > 1.0 and ds_p / dn_p < best_ratio:
                    best_ratio, best_dir = ds_p / dn_p, d
            pair_fn = lambda st: _pair_by_dir(base, best_dir, st, kind, severity)
        else:
            pair_fn = lambda st: confusion_pair(base, kind, severity, st)
        step = 0.12
        rgb_a, rgb_b, dE_n, dE_s = pair_fn(step)
        for _ in range(10):                     # 步长自适应：至目标 / 出界(残差超cap) / 步长上限
            if dE_n >= _DN_TARGET or dE_s > _DS_CAP or step >= 0.6:
                break
            step *= 1.25
            rgb_a, rgb_b, dE_n, dE_s = pair_fn(step)
        if dE_s > _DS_CAP:                      # 超 cap → 回退半步取最后合规值
            rgb_a, rgb_b, dE_n, dE_s = pair_fn(step / 1.25)
        if dE_s <= _DS_CAP and dE_n >= _DN_FLOOR:
            key = (2, dE_n)
        elif dE_s <= _DS_CAP:
            key = (1, dE_n)
        else:
            key = (0, -dE_s)
        if best_key is None or key > best_key:
            best_key, best = key, (base, step, rgb_a, rgb_b, dE_n, dE_s)
    return best


def _family_variants(rgb_a, rgb_b, d, kind, severity, n_off=(0.0, 0.035, 0.07)):
    """多色族：前/背景各 3 变体，沿零空间方向向"远离对方"侧小偏移（线性域 t）。

    真石原板是多板设计（前景/背景各 2~4 个相近色）——单一色对 + 噪声看起来像
    "噪点图"。同线各点在 deutan/protan 模拟后塌缩同一点 → 族间任意对 dE_s 不升；
    但色域边缘 clip 会让变体偏离零空间（残差上升）→ 逐对校验按 _DS_CAP 严格
    执行（不放水），超 cap 的变体整点弃用。
    返回 (ok_fg, ok_bg, dE_n_min)：dE_n_min = 族间最弱对的正常对比（全板可读性下限）。
    """
    from .color_diff import _linear_to_srgb, _srgb_to_linear
    d = np.asarray(d, float)
    la = _srgb_to_linear(np.asarray(rgb_a, dtype=np.float64))
    lb = _srgb_to_linear(np.asarray(rgb_b, dtype=np.float64))
    fg_all = [np.clip(_linear_to_srgb(la - t * d), 0, 255) for t in n_off]   # a 在 -d 侧，再往 -d 推
    bg_all = [np.clip(_linear_to_srgb(lb + t * d), 0, 255) for t in n_off]   # b 在 +d 侧，再往 +d 推

    def _ds(f, b):
        return float(ciede2000(srgb2lab(simulate_cvd(f, kind, severity)),
                               srgb2lab(simulate_cvd(b, kind, severity))))

    ok_fg = [f for f in fg_all if all(_ds(f, b) <= _DS_CAP for b in bg_all)]
    ok_bg = [b for b in bg_all if all(_ds(f, b) <= _DS_CAP for f in fg_all)]
    ok_fg = ok_fg or [np.asarray(rgb_a, dtype=np.float64)]
    ok_bg = ok_bg or [np.asarray(rgb_b, dtype=np.float64)]
    dE_n_min = min(float(ciede2000(srgb2lab(f), srgb2lab(b)))
                   for f in ok_fg for b in ok_bg)
    return ok_fg, ok_bg, dE_n_min


def _align_lightness(fg_list, bg_list):
    """两族平均 L* 拉平（真板精髓：明度零线索，差异全部落在色相/彩度）。

    各组 Lab 沿 L 平移 ≤0.75（合计 ≤1.5，感知不可辨），回 sRGB clip。
    """
    lf = float(np.mean([srgb2lab(np.asarray(f, dtype=np.float64))[0] for f in fg_list]))
    lb_ = float(np.mean([srgb2lab(np.asarray(b, dtype=np.float64))[0] for b in bg_list]))
    half = float(np.clip(lf - lb_, -1.0, 1.0)) / 2.0   # 限幅 ±1.0（明度残差压进量化噪声量级）

    def _shift(lst, dl):
        out = []
        for c in lst:
            lab = srgb2lab(np.asarray(c, dtype=np.float64)).astype(float)
            lab[0] += dl
            out.append(np.clip(lab2srgb(lab), 0, 255))
        return out

    return _shift(fg_list, -half), _shift(bg_list, +half)



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
        info  {digit/kind/severity/step/rgb_a/rgb_b/dE_normal/dE_sim,
               dE_n_min_pair, n_fg, n_bg, design}——v3 起含多色族元信息；
               r_min/r_max 现为点半径双峰的下/上界（70% 大点 + 30% 小点）
    """
    rng = np.random.default_rng(seed)
    mask = _digit_mask(digit, size, font_path)

    # 混淆对构造（2026-09-20 v3：全局择优 + 多色族 + 等明度）：
    #   _pair_best：48 base × 自适应步长——deutan/protan 沿零空间方向把正常对比拉到 20+
    #   （真板可读性水平；旧版 11.5 即停，浪费了可用对比度），tritan 由 dE_s≤2.5 物理上限
    #   主导（自适应停在 cap 附近 ≈12-13）；_family_variants：前/背景各 3 变体（真板多板
    #   设计，族间最弱对仍达标）；_align_lightness：两族平均 L* 拉平——明度零线索
    #   （差异全部落在色相/彩度）。
    base, step, rgb_a, rgb_b, dE_n, dE_s = _pair_best(rng, kind, severity)
    d = np.asarray(confusion_direction(kind, severity), float)
    fg_v, bg_v, dE_n_min = _family_variants(rgb_a, rgb_b, d, kind, severity)
    fg_v, bg_v = _align_lightness(fg_v, bg_v)

    # 圆点填充（2026-09-20 v3）：多色族 + Lab 等明度抖动 + 边界犬牙交错 + 双峰半径
    #   - fg×bg 各 3 变体随机取用：真板多板观感（单一色对像噪点图）
    #   - 抖动改 Lab 空间同分布（L±1.5 / ab±1.2）：明度锁死后差异全在色相；模拟后两族
    #     依旧同分布 → region 对比度照常坍缩（selftest 口径不变）
    #   - 数字边界带内 P=0.35 翻族：犬牙交错，防"靠边缘锐度读数"
    #   - 底色=背景族基色（露底融入背景，不再出现第三色白底）；半径双峰加大
    #     （70% 大点 8~11 / 30% 小点 4~6，直径≥栅格间距）→ 全覆盖无白底
    img = np.full((size, size, 3), 242, dtype=np.float64)
    img[:] = bg_v[0]
    k3 = np.ones((3, 3), np.uint8)
    mask_u8 = mask.astype(np.uint8) * 255
    edge = (cv2.dilate(mask_u8, k3) != cv2.erode(mask_u8, k3))
    r_hi = max(int(r_max) + 2, 11)
    r_lo = max(3, min(int(r_min), 4))
    for gy in range(dot_step, size, dot_step):
        for gx in range(dot_step, size, dot_step):
            cx = int(gx + rng.uniform(-4, 4))
            cy = int(gy + rng.uniform(-4, 4))
            r = int(rng.uniform(8, r_hi)) if rng.random() < 0.7 else int(rng.uniform(r_lo, 6))
            use_fg = bool(mask[cy, cx])
            if edge[cy, cx] and rng.random() < 0.35:
                use_fg = not use_fg               # 边界带交错
            fam = fg_v if use_fg else bg_v
            base_pt = fam[int(rng.integers(0, len(fam)))]
            lab = srgb2lab(base_pt).astype(float)
            lab += [rng.uniform(-1.5, 1.5), rng.uniform(-1.2, 1.2), rng.uniform(-1.2, 1.2)]
            col = np.clip(lab2srgb(lab), 0, 255).round().astype(int)
            cv2.circle(img, (cx, cy), r, col.tolist(), -1, lineType=cv2.LINE_AA)

    info = {
        "digit": str(digit), "kind": kind, "severity": severity, "step": step,
        "rgb_a": rgb_a.round(1).tolist(), "rgb_b": rgb_b.round(1).tolist(),
        "dE_normal": dE_n, "dE_sim": dE_s,
        "dE_n_min_pair": round(dE_n_min, 2),    # 族间最弱对（全板可读性下限）
        "n_fg": len(fg_v), "n_bg": len(bg_v),   # 多色族变体数（真板多板设计）
        "design": "family-v2",
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
