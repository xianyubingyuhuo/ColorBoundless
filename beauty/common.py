# -*- coding: utf-8 -*-
"""beauty 公共层：所有品类模块共享的工具函数与模型加载

为什么提取公共层？
    lipstick / eyebrow / eyeshadow 都要用：颜色转换、图像保存、人脸分割、Lab 换色。
    提取到这里，各模块只写自己的"业务逻辑"，不重复造轮子。

包含：
    hex2bgr            HEX 色号 → BGR
    save_img           保存图片（规避中文路径问题）
    load_parsing_net   加载 BiSeNet 人脸解析模型
    segment            BiSeNet 分割 → 19 类 parsing 图
    apply_region_color 通用区域换色（Lab 混合保留明度纹理 + 羽化）
"""
import os
import sys

import cv2
import numpy as np
import torch
from PIL import Image
import torchvision.transforms as transforms

# BiSeNet 定义已 vendor 进仓库（cv/face_parsing，MIT，来源见该目录 README）
from cv.face_parsing import BiSeNet  # noqa: E402

# 项目根目录 ColorBoundless/
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_WEIGHTS = os.path.join(_BASE, "models", "face_parsing", "79999_iter.pth")
RESULT_DIR = os.path.join(_BASE, "results", "tryon")


def hex2bgr(h):
    """HEX 色号（如 'FF4D6D' 或 '#FF4D6D'）→ BGR 列表"""
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


def load_parsing_net(weights=DEFAULT_WEIGHTS, device=None):
    """加载 BiSeNet 人脸解析模型，返回 (net, device)"""
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    net = BiSeNet(n_classes=19)
    net.load_state_dict(torch.load(weights, map_location=device))
    net.to(device).eval()
    print(f"[OK] 模型: {weights} | device: {device}")
    return net, device


def segment(net, img_pil, device):
    """输入 PIL 图片，输出 (512, 512) 的 19 类 parsing 图（argmax 后的类别索引）"""
    to_tensor = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
    ])
    image = img_pil.resize((512, 512), Image.BILINEAR)
    x = to_tensor(image).unsqueeze(0).to(device)
    with torch.no_grad():
        out = net(x)[0]
    return out.squeeze(0).cpu().numpy().argmax(0)


def apply_region_color(image_bgr, mask, color_bgr, alpha=0.7, feather=3.0):
    """通用区域换色：Lab 空间混合（只改 a/b 保留 L 明度纹理）+ 边缘羽化

    参数：
        image_bgr : BGR 原图
        mask      : 二维掩膜（1 = 目标区域），0~1 float 或 0/255 uint8 均可
        color_bgr : 目标色（BGR 列表）
        alpha     : 颜色强度（0~1，越大越接近目标色）
        feather   : 边缘羽化 sigma（越大过渡越柔）
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
