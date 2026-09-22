# -*- coding: utf-8 -*-
"""def 43 · 人脸属性档案：白平衡校正 + BiSeNet 部位解析 → 结构化五官取色档案。

设计决策：
1. 色偏对策（用户反馈：有的照片颜色有误差，白皮可能拍成黄皮）：
   - Gray-World 温和白平衡（gain 限幅 [0.80,1.25] + 0.65 混合，防过校正）；
   - 双版本取色择优：原图 / 校正图各自在 skin mask 上统计中值色，
     按 YCbCr 经验肤色域（Cb∈[77,127] Cr∈[133,177]）算偏离分，分低者胜——
     校正歪了自动回退原图版，从机制上防「越校越黄」；
   - 肤色域总分超阈值（浓妆/滤镜脸）时 quality 注记「仅供参考」。
2. 取色卫生：每类 mask 先 erode 去边缘（贴脸发丝/妆边混色像素），中值色抗
   高光与噪点；虹膜只取眼裂中心小椭圆（eye 类含眼白），剔除眼白高光像素。
3. 分类口径：肤色走 ITA°（Chardon 六档）+ a*/(a*+b*) 冷暖比；发眉瞳唇走
   L* 亮度分档 + b*-a* 金调条件 + a* 红调条件；脸型 = skin 类宽高比三档
   （CelebAMask 的 skin 不含脖颈，额头可能被刘海占用 → 标注「粗略估计」）。
4. 质量降级不瞒报：mask 面积不足 → status="unknown"（面积不足）；检测到
   眼镜类(6) → 瞳色注记「仅供参考」。前端对 unknown 灰显，AI 消息里如实带出。
5. 边界：本模块不加载 torch（BiSeNet 由调用方传入，复用 tryon_service 单例）；
   输出纯数据 dict，五件套壳由 tryon_service.run_face_profile 包裹。
"""
import math

import cv2
import numpy as np

# celebAMask 19 类编号（与 tryon_service._REGION_PARTS 同源）
SKIN, LBROW, RBROW, LEYE, REYE, EYEG = 1, 2, 3, 4, 5, 6
ULIP, LLIP, NECK, HAIR, HAT = 12, 13, 14, 17, 18

# ---- 质量阈值（mask 像素占全图比例，低于即判 unknown）----
_MIN_RATIO = {"skin": 0.04, "hair": 0.025, "brow": 0.0015, "eye": 0.002, "lip": 0.0035}
# 肤色域得分超过该值 → 浓妆/滤镜/极端光线，注记仅供参考
_SKIN_DOMAIN_WARN = 9.0


# ---------------------------------------------------------------------------
# 白平衡（def 43 · Gray-World 温和版：gain 限幅 + 混合，防过校正）
# ---------------------------------------------------------------------------
def white_balance(img_bgr, mix=0.65, gain_clamp=(0.80, 1.25)):
    """Gray-World 白平衡：三通道均值拉齐灰世界假设。

    mix 为校正强度（0=原图，1=完全校正）；gain_clamp 限幅防止夜景/大面积
    单色背景把 gain 拉飞。返回 (校正图 float32 BGR, gains[B,G,R])。
    """
    f = img_bgr.astype(np.float32)
    means = f.reshape(-1, 3).mean(axis=0)                 # B, G, R
    gray = float(means.mean())
    gains = gray / np.maximum(means, 1e-6)
    gains = np.clip(gains, gain_clamp[0], gain_clamp[1]).astype(np.float32)
    corrected = f * gains.reshape(1, 1, 3)
    out = f * (1.0 - mix) + corrected * mix
    return np.clip(out, 0, 255), gains


# ---------------------------------------------------------------------------
# 掩码卫生与统计
# ---------------------------------------------------------------------------
def _erode(mask, k=5, it=2):
    """erode 去边缘混色像素；全蚀光则回退原掩码（小部件保底）。"""
    m = (mask > 0).astype(np.uint8)
    out = cv2.erode(m, np.ones((k, k), np.uint8), iterations=it)
    return out if out.sum() >= 30 else m


def _median_bgr(img_bgr, mask):
    """mask 内中值色（BGR float32 数组或 None=掩码为空）。"""
    ys, xs = np.where(mask > 0)
    if len(xs) < 10:
        return None
    return np.median(img_bgr[ys, xs], axis=0)


def _lab_float(img_bgr):
    """全图 Lab float32（H,W,3）：L∈[0,100]，a/b 已去 128 偏置。"""
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L = lab[..., 0] * (100.0 / 255.0)
    return L, lab[..., 1] - 128.0, lab[..., 2] - 128.0


def _hex_of(med_bgr):
    """BGR 中值数组 → RRGGBB 大写 hex。"""
    b, g, r = [int(round(float(v))) for v in med_bgr]
    return "%02X%02X%02X" % (r, g, b)


# ---------------------------------------------------------------------------
# 肤色：ITA° 分档 + 冷暖底调 + 肤色域判分
# ---------------------------------------------------------------------------
def _skin_domain_score(bgr):
    """YCbCr 经验肤色域偏离分（越小越像自然肤色）。Cb∈[77,127] Cr∈[133,177]。"""
    ycc = cv2.cvtColor(np.uint8([[list(bgr)]]), cv2.COLOR_BGR2YCrCb)[0, 0]
    cb, cr = float(ycc[2]), float(ycc[1])
    return ((cb - 102.0) / 25.0) ** 2 + ((cr - 155.0) / 22.0) ** 2


def _ita_level(ita):
    """ITA°（Chardon 分型）→ 中文档位。"""
    if ita > 55: return "极白皙"
    if ita > 41: return "白皙"
    if ita > 28: return "自然"
    if ita > 10: return "小麦"
    if ita > -30: return "浅棕"
    return "深棕"


def _undertone(a, b):
    """冷暖底调：a*/(a*+b*) 比值。黄皮 b* 主导（比值小），粉皮 a* 主导。"""
    s = a + b
    if s < 12:
        return "难以判断（色彩信息不足）"
    r = a / s
    if r <= 0.42: return "暖调（黄调）"
    if r >= 0.50: return "冷调（粉调）"
    return "中性"


def _skin_from(img_bgr, parsing):
    """单图肤色统计 → {hex, L, a, b, ita, level, undertone} 或 None。"""
    skin = _erode(parsing == SKIN)
    med = _median_bgr(img_bgr, skin)
    if med is None:
        return None
    L, A, B = _lab_float(img_bgr)
    ys, xs = np.where(skin > 0)
    Lm = float(np.median(L[ys, xs]))
    am = float(np.median(A[ys, xs]))
    bm = float(np.median(B[ys, xs]))
    ita = math.degrees(math.atan2(Lm - 50.0, bm)) if abs(bm) > 1e-6 else 90.0
    return {"hex": _hex_of(med), "L": Lm, "a": am, "b": bm,
            "ita": round(ita, 1), "level": _ita_level(ita),
            "undertone": _undertone(am, bm)}


# ---------------------------------------------------------------------------
# 发 / 眉 / 瞳 / 唇 分类（L* 亮度分档 + 金调/红调条件）
# ---------------------------------------------------------------------------
def _hair_name(Lm, am, bm, sat):
    if am > bm + 6 and Lm >= 35:
        return "红铜色"
    if Lm < 22: return "黑色"
    if Lm < 38: return "深棕"
    if Lm < 52:
        return "深金色" if (bm - am > 20 and sat > 0.25) else "棕色"
    if Lm < 66:
        return "金棕色" if (bm - am > 18 and sat > 0.25) else "浅棕"
    if sat < 0.12: return "灰白色"
    return "浅金色"


def _brow_name(Lm):
    if Lm < 25: return "深黑"
    if Lm < 40: return "深棕"
    if Lm < 55: return "棕色"
    return "浅棕"


def _eye_name(Lm, am, bm):
    if Lm < 30: return "深棕"
    if Lm < 48: return "棕色"
    if Lm < 62:
        return "琥珀色" if (bm - am > 15) else "浅棕"
    if bm - am > 15: return "琥珀色"
    if am > bm + 4: return "灰绿色"
    return "浅色（少见）"


def _lip_name(Lm, am):
    if Lm >= 68 and am < 14: return "浅淡"
    if am >= 20 and Lm >= 45: return "红润"
    if Lm < 40: return "深暗"
    return "自然粉"


# ---------------------------------------------------------------------------
# 瞳色：眼裂中心小椭圆（eye 类含眼白，只取中心虹膜带，剔除眼白高光）
# ---------------------------------------------------------------------------
def _iris_bgr(img_bgr, parsing):
    eye = np.isin(parsing, (LEYE, REYE)).astype(np.uint8)
    n, lab_cc, stats, _ = cv2.connectedComponentsWithStats(eye, 8)
    best = None                                   # (面积, 中值色) —— 取眼裂最大那只
    for i in range(1, n):
        x, y, w, h, area = [int(v) for v in stats[i]]
        if area < 12:
            continue
        cx, cy = x + w // 2, y + h // 2
        rw, rh = max(2, int(w * 0.28)), max(2, int(h * 0.30))
        oval = np.zeros_like(eye)
        cv2.ellipse(oval, (cx, cy), (rw, rh), 0, 0, 360, 1, -1)
        m = (oval == 1) & (lab_cc == i)
        ys, xs = np.where(m)
        if len(xs) < 20:
            continue
        pix = img_bgr[ys, xs]
        lab_pix = cv2.cvtColor(pix.reshape(1, -1, 3), cv2.COLOR_BGR2LAB)[0].astype(np.float32)
        keep = ~((lab_pix[:, 0] > 190) & (lab_pix[:, 2] < 150))   # 剔眼白高光
        med = np.median(pix[keep] if keep.sum() >= 20 else pix, axis=0)
        if best is None or area > best[0]:
            best = (area, med)
    return None if best is None else best[1]


# ---------------------------------------------------------------------------
# 脸型：skin 类（不含脖颈）宽高比三档 + 下颌宽比
# ---------------------------------------------------------------------------
def _face_shape(parsing):
    skin = (parsing == SKIN).astype(np.uint8)
    n, _, stats, _ = cv2.connectedComponentsWithStats(skin, 8)
    if n < 2:
        return {"status": "unknown", "note": "未检测到脸部区域"}
    areas = [int(s[4]) for s in stats[1:]]
    x, y, w, h = [int(v) for v in stats[1 + int(np.argmax(areas))][:4]]   # 最大连通域=脸
    if h < 20 or w < 20:
        return {"status": "unknown", "note": "脸部区域过小"}
    band = skin[y:y + h, x:x + w]
    mid = band[int(h * 0.40):int(h * 0.60)]       # 中部带（颧骨宽）
    low = band[int(h * 0.75):]                    # 下部带（下颌）
    w_mid = max(1, int((mid > 0).sum(axis=1).mean()))
    w_low = max(1, int((low > 0).sum(axis=1).mean()))
    ratio = h / float(w_mid)
    jaw = w_low / float(w_mid)
    if ratio > 1.45:
        name = "偏长"
    elif ratio < 1.15:
        name = "偏圆"
    else:
        name = "椭圆" + ("·下巴偏尖" if jaw < 0.62 else "")
    return {"status": "ok", "name": name, "ratio": round(ratio, 2),
            "note": "粗略估计（受发型/拍摄角度影响）"}


# ---------------------------------------------------------------------------
# 主入口：analyze（parsing 由调用方传入，torch 留在服务层）
# ---------------------------------------------------------------------------
def analyze(img_bgr, parsing):
    """输入原图 BGR + 解析图（512×512 argmax 图，调用方负责 segment）。

    mask 统一来自解析图；取色双版本（原图 / 白平衡校正图）——肤色按
    YCbCr 肤色域得分择优，其余部位用原图（部件色偏影响小，保留真实固有色）。
    返回 profile dict（纯数据，无五件套壳）。
    """
    H, W = img_bgr.shape[:2]
    total = float(H * W)
    img_wb_f, gains_bgr = white_balance(img_bgr)
    img_wb = np.clip(img_wb_f, 0, 255).astype(np.uint8)
    lab_orig = _lab_float(img_bgr)

    ratios = {"skin": float((parsing == SKIN).sum()) / total,
              "hair": float((parsing == HAIR).sum()) / total,
              "brow": float(np.isin(parsing, (LBROW, RBROW)).sum()) / total,
              "eye": float(np.isin(parsing, (LEYE, REYE)).sum()) / total,
              "lip": float(np.isin(parsing, (ULIP, LLIP)).sum()) / total}
    notes = []

    # ---- 肤色：双版本择优（机制性防「白皮拍成黄皮」/「越校越黄」）----
    correction = {"applied": True, "method": "gray-world",
                  "gains": [round(float(gains_bgr[2]), 3), round(float(gains_bgr[1]), 3),
                            round(float(gains_bgr[0]), 3)]}          # 展示顺序 R,G,B
    s_orig = _skin_from(img_bgr, parsing)
    s_wb = _skin_from(img_wb, parsing)
    if s_orig is None and s_wb is None:
        skin = {"status": "unknown", "note": "未检测到足够皮肤区域"}
    else:
        skin_mask = _erode(parsing == SKIN)
        sc_orig = _skin_domain_score(_median_bgr(img_bgr, skin_mask))
        sc_wb = _skin_domain_score(_median_bgr(img_wb, skin_mask))
        if sc_wb <= sc_orig + 0.04:                   # 校正版不差于原图版（小余量=中性先验）
            chosen, sc = (s_wb if s_wb else s_orig), sc_wb
            correction["chosen"] = "white_balanced"
            correction["note"] = "照片已按灰世界假设做白平衡校正后取色"
        else:                                          # 校正反而更偏 → 回退原图
            chosen, sc = (s_orig if s_orig else s_wb), sc_orig
            correction["chosen"] = "original"
            correction["note"] = "白平衡校正使肤色偏离自然域，已按原图取色"
        skin = {"status": "ok", "hex": chosen["hex"], "level": chosen["level"],
                "undertone": chosen["undertone"], "ita": chosen["ita"]}
        if sc > _SKIN_DOMAIN_WARN:
            skin["note"] = "肤色偏离自然范围（浓妆/滤镜/极端光线），结果仅供参考"
            notes.append("皮肤色偏离自然域，检测结果仅供参考")

    # ---- 发色（用原图取色：发色是真实固有色，白平衡会抹掉暖发调）----
    hair_mask = _erode(parsing == HAIR)
    med_hair = _median_bgr(img_bgr, hair_mask)
    if ratios["hair"] < _MIN_RATIO["hair"] or med_hair is None:
        hair = {"status": "unknown", "note": "头发区域过小或被裁切，未取色"}
    else:
        Lh, Ah, Bh = lab_orig
        ys, xs = np.where(hair_mask > 0)
        hsv_s = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)[..., 1].astype(np.float32) / 255.0
        hair = {"status": "ok", "hex": _hex_of(med_hair),
                "name": _hair_name(float(np.median(Lh[ys, xs])), float(np.median(Ah[ys, xs])),
                                   float(np.median(Bh[ys, xs])), float(np.median(hsv_s[ys, xs])))}

    # ---- 眉色 ----
    brow_mask = _erode(np.isin(parsing, (LBROW, RBROW)).astype(np.uint8))
    med_brow = _median_bgr(img_bgr, brow_mask)
    if ratios["brow"] < _MIN_RATIO["brow"] or med_brow is None:
        brow = {"status": "unknown", "note": "眉毛区域过小，未取色"}
    else:
        Lb, _, _ = lab_orig
        ys, xs = np.where(brow_mask > 0)
        brow = {"status": "ok", "hex": _hex_of(med_brow),
                "name": _brow_name(float(np.median(Lb[ys, xs])))}

    # ---- 瞳色（眼镜降级注记）----
    med_eye = _iris_bgr(img_bgr, parsing)
    if ratios["eye"] < _MIN_RATIO["eye"] or med_eye is None:
        eye = {"status": "unknown", "note": "眼部区域过小或闭眼，未取色"}
    else:
        Le, Ae, Be = lab_orig
        y_e, x_e = np.where(np.isin(parsing, (LEYE, REYE)))
        eye = {"status": "ok", "hex": _hex_of(med_eye),
               "name": _eye_name(float(np.median(Le[y_e, x_e])),
                                 float(np.median(Ae[y_e, x_e])),
                                 float(np.median(Be[y_e, x_e])))}
        if float((parsing == EYEG).sum()) / total > ratios["eye"] * 0.5:
            eye["note"] = "检测到眼镜，瞳色仅供参考"
            notes.append("佩戴眼镜，瞳色检测精度下降")

    # ---- 唇色 ----
    lip_mask = _erode(np.isin(parsing, (ULIP, LLIP)).astype(np.uint8))
    med_lip = _median_bgr(img_bgr, lip_mask)
    if ratios["lip"] < _MIN_RATIO["lip"] or med_lip is None:
        lip = {"status": "unknown", "note": "唇部区域过小，未取色"}
    else:
        Ll, Al, _ = lab_orig
        ys, xs = np.where(lip_mask > 0)
        lip = {"status": "ok", "hex": _hex_of(med_lip),
               "name": _lip_name(float(np.median(Ll[ys, xs])), float(np.median(Al[ys, xs])))}

    return {"skin": skin, "hair": hair, "brow": brow, "eye": eye, "lip": lip,
            "face_shape": _face_shape(parsing),
            "correction": correction,
            "quality": {"ratios": {k: round(v, 4) for k, v in ratios.items()},
                        "notes": notes}}

    if ratio > 1.45:
        name = "偏长"
    elif ratio < 1.15:
        name = "偏圆"
    else:
        name = "椭圆" + ("·下巴偏尖" if jaw < 0.62 else "")
    return {"status": "ok", "name": name, "ratio": round(ratio, 2),
            "note": "粗略估计（受发型/拍摄角度影响）"}

