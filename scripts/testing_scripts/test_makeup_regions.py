# -*- coding: utf-8 -*-
"""
test_makeup_regions.py
======================
测试眉毛 / 眼影的颜色更改（人脸分割 + Lab 换色）

背景：
    lipstick/tryon.py 已验证嘴唇（part 12, 13）可上色。
    本脚本测试：
      - 眉毛：part 2（左眉）+ 3（右眉）
      - 眼影：part 4（左眼）+ 5（右眼）区域
    并输出对比图，直观确认效果。

BiSeNet 类别（19 类）：
    1 skin, 2 l_brow, 3 r_brow, 4 l_eye, 5 r_eye, 6 eye_g,
    12 u_lip, 13 l_lip, ...

用法：
    python scripts/test_makeup_regions.py
    输出到 results/tryon_regions/
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
import torchvision.transforms as transforms

# ---------- 引用 lipstick.tryon 的复用函数 ----------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIPSTICK_DIR = PROJECT_ROOT / "beauty" / "lipstick"
sys.path.insert(0, str(LIPSTICK_DIR))
from tryon import hex2bgr, save_img, segment  # noqa: E402

# 人脸解析库 + 模型
_PARSE_LIB = PROJECT_ROOT.parent / "face-parsing.PyTorch"
sys.path.insert(0, str(_PARSE_LIB))
from model import BiSeNet  # noqa: E402

WEIGHTS = PROJECT_ROOT / "models" / "face_parsing" / "79999_iter.pth"
TEST_IMG = PROJECT_ROOT / "data" / "faces" / "11053.jpg"
RESULT_DIR = PROJECT_ROOT / "results" / "tryon_regions"

# 类别
BROWS = (2, 3)    # 左眉 + 右眉
EYES = (4, 5)     # 左眼 + 右眼（作为眼影区域近似）
LIPS = (12, 13)   # 上唇 + 下唇


def apply_region_color(image_bgr, mask, color_bgr,
                       alpha=0.7, feather=3.0):
    """通用区域换色：Lab 空间混合（保留明度纹理）+ 边缘羽化
    mask: 二维 uint8/float 掩膜（1 = 目标区域）
    """
    img_f = image_bgr.astype(np.float32) / 255.0

    # Lab 颜色迁移：只改 a/b，保留 L（亮度/纹理）
    lab = cv2.cvtColor(img_f, cv2.COLOR_BGR2LAB)
    tar = np.array([[color_bgr]], dtype=np.float32) / 255.0
    tar_lab = cv2.cvtColor(tar, cv2.COLOR_BGR2LAB)
    L, A, B = cv2.split(lab)
    tl, ta, tb = tar_lab[0, 0, :]
    new_a = A * (1 - alpha) + ta * alpha
    new_b = B * (1 - alpha) + tb * alpha
    changed = cv2.cvtColor(cv2.merge([L, new_a, new_b]), cv2.COLOR_LAB2BGR)

    # 区域掩膜 + 羽化
    mask_f = mask.astype(np.float32)
    mask_f = cv2.GaussianBlur(mask_f, (0, 0), sigmaX=feather)
    mask_f = mask_f[..., None]

    result = changed * mask_f + img_f * (1 - mask_f)
    return np.clip(result * 255, 0, 255).astype(np.uint8)


def get_eyeshadow_mask(parsing, eye_parts=(4, 5)):
    """眼影掩膜 = 眼睛区域上方的"眼皮"带（避开眼球和眉毛）
    方法：对每只眼睛的边界框，取其上方 band_h 高度的带状区域。
    """
    eye_mask = np.isin(parsing, eye_parts).astype(np.uint8)
    n, _, stats, _ = cv2.connectedComponentsWithStats(eye_mask, connectivity=8)
    shadow_mask = np.zeros_like(eye_mask, dtype=np.uint8)

    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 50:  # 忽略噪声
            continue
        band_h = int(round(h * 0.9))       # 带高 = 眼睛高度
        top = max(0, y - band_h)           # 眼睛上边界往上
        pad_w = max(4, int(w * 0.1))       # 左右略扩
        shadow_mask[top:y, max(0, x - pad_w):min(eye_mask.shape[1], x + w + pad_w)] = 1

    # 排除眉毛（part 2, 3），避免眼影和眉毛重叠
    shadow_mask[parsing == 2] = 0
    shadow_mask[parsing == 3] = 0
    return shadow_mask


def vis_parsing(parsing, parts, name):
    """生成指定部位的可视化掩膜图（白=目标区域）"""
    mask = np.isin(parsing, parts).astype(np.uint8) * 255
    save_img(str(RESULT_DIR / f"{name}_mask.png"), mask, ".png")


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    # ---------- 1. 加载模型 ----------
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = BiSeNet(n_classes=19)
    net.load_state_dict(torch.load(str(WEIGHTS), map_location=device))
    net.to(device).eval()
    print(f"[OK] 模型加载: {WEIGHTS.name} | device: {device}")

    # ---------- 2. 分割 ----------
    img = Image.open(str(TEST_IMG))
    parsing = segment(net, img, device)  # (512, 512) 类别图
    img_bgr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    H, W = img_bgr.shape[:2]
    p = cv2.resize(parsing, (W, H), interpolation=cv2.INTER_NEAREST)

    # 统计各部位像素数，确认分割是否命中
    for name, parts in [("眉毛", BROWS), ("眼睛/眼影", EYES), ("嘴唇", LIPS)]:
        cnt = int(np.isin(p, parts).sum())
        print(f"  [{name}] parts={parts} 命中像素: {cnt}")
        if cnt < 50:
            print(f"    ⚠️ 像素太少，可能没检测到该部位！")

    # ---------- 3. 分别上妆 ----------
    brow_color = hex2bgr("6B4A2B")     # 深棕色眉毛
    eye_color = hex2bgr("F2B6C5")      # 粉色眼影
    lip_color = hex2bgr("D81B60")      # 玫红嘴唇（对照）

    mask_brows = np.isin(p, BROWS).astype(np.float32)
    mask_eyes = get_eyeshadow_mask(p)  # 眼皮区域（避开眼球）
    mask_lips = np.isin(p, LIPS).astype(np.float32)

    img_brows = apply_region_color(img_bgr, mask_brows, brow_color, alpha=0.8, feather=2.0)
    img_eyes = apply_region_color(img_bgr, mask_eyes, eye_color, alpha=0.55, feather=4.0)
    img_lips = apply_region_color(img_bgr, mask_lips, lip_color, alpha=0.75, feather=2.0)

    # ---------- 4. 保存结果 ----------
    save_img(str(RESULT_DIR / "original.png"), img_bgr, ".png")
    save_img(str(RESULT_DIR / "brow.png"), img_brows, ".png")
    save_img(str(RESULT_DIR / "eyeshadow.png"), img_eyes, ".png")
    save_img(str(RESULT_DIR / "lip.png"), img_lips, ".png")

    # 掩膜可视化
    save_img(str(RESULT_DIR / "brow_mask.png"),
             (mask_brows * 255).astype(np.uint8), ".png")
    save_img(str(RESULT_DIR / "eyeshadow_mask.png"),
             (mask_eyes * 255).astype(np.uint8), ".png")
    save_img(str(RESULT_DIR / "lip_mask.png"),
             (mask_lips * 255).astype(np.uint8), ".png")

    # 三张对比图
    save_img(str(RESULT_DIR / "compare_brow.jpg"),
             np.hstack([img_bgr, img_brows]), ".jpg", 95)
    save_img(str(RESULT_DIR / "compare_eyeshadow.jpg"),
             np.hstack([img_bgr, img_eyes]), ".jpg", 95)
    save_img(str(RESULT_DIR / "compare_lip.jpg"),
             np.hstack([img_bgr, img_lips]), ".jpg", 95)

    print(f"\n✅ 完成！结果目录: {RESULT_DIR}")
    print("  compare_brow.jpg      = 原图 vs 棕色眉毛")
    print("  compare_eyeshadow.jpg = 原图 vs 粉色眼影")
    print("  compare_lip.jpg       = 原图 vs 玫红嘴唇（对照）")
    print("  *_mask.png            = 各部位分割掩膜（检查命中区域）")


if __name__ == "__main__":
    main()
