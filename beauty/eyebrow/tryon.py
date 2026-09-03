# -*- coding: utf-8 -*-
"""眉毛虚拟试妆模块（ColorBoundless 业务代码）

复用 beauty/common.py 的公共能力，只实现眉毛（BiSeNet part 2, 3）的换色。
接口与 lipstick/tryon.py 对齐，方便上层统一调用。

用法：
    from beauty import eyebrow
    eyebrow.tryon("photo.jpg", color="6B4A2B")
    # 或
    from beauty.eyebrow.tryon import tryon
    tryon("photo.jpg", color="6B4A2B")
"""
import os

import cv2
import numpy as np
from PIL import Image

from .. import common

# BiSeNet 类别：2 = 左眉(l_brow)，3 = 右眉(r_brow)
BROWS = (2, 3)


def tryon(img_path, color="6B4A2B", weights=common.DEFAULT_WEIGHTS, out="",
          alpha=0.8, feather=2.0, device=None):
    """眉毛试妆接口：输入图片路径 + 眉色(HEX str)，输出上妆图，返回输出目录

    参数：
        img_path : 输入图片路径
        color    : 眉色 HEX（如 '6B4A2B' 深棕）
        weights  : BiSeNet 权重路径
        out      : 输出子目录名（默认用色号名）
        alpha    : 颜色强度（眉毛建议 0.7~0.9）
        feather  : 边缘羽化 sigma
        device   : 'cuda'/'cpu'，默认自动
    示例：tryon("photo.jpg", color="6B4A2B", alpha=0.8)
    """
    net, device = common.load_parsing_net(weights, device)

    img = Image.open(img_path)
    parsing = common.segment(net, img, device)
    bgr = common.hex2bgr(color)
    img_bgr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    H, W = img_bgr.shape[:2]
    p = cv2.resize(parsing, (W, H), interpolation=cv2.INTER_NEAREST)

    # 眉毛掩膜（part 2 + 3）
    mask = np.isin(p, BROWS).astype(np.float32)
    cnt = int(mask.sum())
    if cnt < 50:
        print(f"⚠️ 眉毛像素太少（{cnt}），可能没检测到眉毛，效果可能不佳")

    out_img = common.apply_region_color(img_bgr, mask, bgr, alpha=alpha, feather=feather)

    # 保存输出（对齐 lipstick 的目录结构）
    out_name = out if out else color
    respth = os.path.join(common.RESULT_DIR, "eyebrow", out_name)
    os.makedirs(respth, exist_ok=True)
    common.save_img(os.path.join(respth, "original.png"), img_bgr, ".png")
    common.save_img(os.path.join(respth, "makeup.png"), out_img, ".png")
    combined = np.hstack([img_bgr, out_img])
    common.save_img(os.path.join(respth, "compare.jpg"), combined, ".jpg", 95)
    print(f"[OK] 眉色 #{color} 完成 -> {os.path.join(respth, 'compare.jpg')}")
    return respth


if __name__ == "__main__":
    import sys as _sys
    _img = _sys.argv[1] if len(_sys.argv) > 1 else "photo.jpg"
    _color = _sys.argv[2] if len(_sys.argv) > 2 else "6B4A2B"
    tryon(_img, color=_color)
