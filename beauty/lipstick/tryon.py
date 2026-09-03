# -*- encoding: utf-8 -*-
"""口红虚拟试妆模块（ColorBoundless 业务代码）
依赖:
  - 公共库 face-parsing.PyTorch 提供 BiSeNet 模型
  - models/face_parsing/79999_iter.pth 分割权重
用法:
  from lipstick.tryon import tryon
  from lipstick.shade_library import search_shade
  chosen = search_shade("FF4D6D", top_k=1)[0]
  tryon("photo.jpg", color=chosen["hex"])
"""
import os
import sys

import numpy as np
import cv2
import torch
from PIL import Image
import torchvision.transforms as transforms

# BiSeNet 定义已 vendor 进仓库（cv/face_parsing，MIT，来源见该目录 README）
from cv.face_parsing import BiSeNet  # noqa: E402

# 项目根目录 ColorBoundless/
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_WEIGHTS = os.path.join(_BASE, "models", "face_parsing", "79999_iter.pth")
RESULT_DIR = os.path.join(_BASE, "results", "tryon")


def hex2bgr(h):
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return [b, g, r]


def save_img(path, img_bgr, ext=".jpg", quality=95):
    """用 imencode + 原生写文件，规避 cv2.imwrite 对中文路径失败的问题"""
    params = [int(cv2.IMWRITE_JPEG_QUALITY), quality] if ext.lower() in (".jpg", ".jpeg") else []
    ok, buf = cv2.imencode(ext, img_bgr, params)
    if not ok:
        raise RuntimeError("imencode 失败: " + path)
    with open(path, "wb") as f:
        f.write(buf.tobytes())


def apply_lip_color(image_bgr, parsing, part, color_bgr, alpha=0.75, feather=2.0, gloss=0.3):
    """完整版口红后处理:
    1) Lab 颜色迁移(保留明度纹理) 2) 边缘羽化 3) 高光润泽
    """
    img_f = image_bgr.astype(np.float32) / 255.0

    lab = cv2.cvtColor(img_f, cv2.COLOR_BGR2LAB)
    tar = np.array([[color_bgr]], dtype=np.float32) / 255.0
    tar_lab = cv2.cvtColor(tar, cv2.COLOR_BGR2LAB)
    L, A, B = cv2.split(lab)
    tl, ta, tb = tar_lab[0, 0, :]
    new_a = A * (1 - alpha) + ta * alpha
    new_b = B * (1 - alpha) + tb * alpha
    changed = cv2.cvtColor(cv2.merge([L, new_a, new_b]), cv2.COLOR_LAB2BGR)

    mask = (parsing == part).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=feather)
    mask = mask[..., None]

    if gloss > 0:
        v = cv2.cvtColor(img_f, cv2.COLOR_BGR2HSV)[..., 2]
        gloss_mask = np.clip((v - 0.72) * 5, 0, 1) * (parsing == part).astype(np.float32)
        gloss_mask = cv2.GaussianBlur(gloss_mask, (0, 0), sigmaX=1.0)[..., None]
        changed = changed * (1 + gloss * gloss_mask * 0.35)

    result = changed * mask + img_f * (1 - mask)
    return np.clip(result * 255, 0, 255).astype(np.uint8)


def segment(net, img_pil, device):
    to_tensor = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
    ])
    image = img_pil.resize((512, 512), Image.BILINEAR)
    x = to_tensor(image).unsqueeze(0).to(device)
    with torch.no_grad():
        out = net(x)[0]
    return out.squeeze(0).cpu().numpy().argmax(0)


def tryon(img_path, color="FF4D6D", weights=DEFAULT_WEIGHTS, out="",
          alpha=0.75, feather=2.0, gloss=0.3, device=None):
    """试妆接口: 输入图片路径 + 色号(HEX str), 输出上妆图, 返回输出目录
    示例: tryon("photo.jpg", color="FF4D6D", alpha=0.8)
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    net = BiSeNet(n_classes=19)
    net.load_state_dict(torch.load(weights, map_location=device))
    net.to(device).eval()
    print("[OK] 模型:", weights, "| device:", device)

    img = Image.open(img_path)
    parsing = segment(net, img, device)
    bgr = hex2bgr(color)
    img_bgr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    H, W = img_bgr.shape[:2]
    p = cv2.resize(parsing, (W, H), interpolation=cv2.INTER_NEAREST)

    out_img = img_bgr.copy()
    for part in (12, 13):  # 上唇 + 下唇
        out_img = apply_lip_color(out_img, p, part, bgr,
                                  alpha=alpha, feather=feather, gloss=gloss)

    out_name = out if out else color
    respth = os.path.join(RESULT_DIR, out_name)
    os.makedirs(respth, exist_ok=True)
    save_img(os.path.join(respth, "original.png"), img_bgr, ".png")
    save_img(os.path.join(respth, "makeup.png"), out_img, ".png")
    combined = np.hstack([img_bgr, out_img])
    save_img(os.path.join(respth, "compare.jpg"), combined, ".jpg", 95)
    print("[OK] 色号 #%s 完成 -> %s" % (color, os.path.join(respth, "compare.jpg")))
    return respth


if __name__ == "__main__":
    import sys as _sys
    img = _sys.argv[1] if len(_sys.argv) > 1 else "6.jpg"
    color = _sys.argv[2] if len(_sys.argv) > 2 else "FF4D6D"
    tryon(img, color=color)
