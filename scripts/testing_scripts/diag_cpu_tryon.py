# -*- coding: utf-8 -*-
"""diag_cpu_tryon：验证 BiSeNet 试妆在纯 CPU 上的耗时（云服务器部署可行性）

背景：用户部署策略 = 无 GPU 学生服务器 + DeepSeek API（本地 4080 只用于录视频）。
关键疑问：BiSeNet 人脸解析在服务器 CPU 上单张图要多久？>5s 体验差，<2s 可上线。
方法：强制 device="cpu"，分别计时 模型加载 / 首次分割 / 二次分割 / 换色。
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2                                              # noqa: E402
import numpy as np                                      # noqa: E402
from PIL import Image                                   # noqa: E402

from beauty.common import (                             # noqa: E402
    apply_region_color, load_parsing_net, segment)

IMG = Path(__file__).resolve().parents[2] / "data" / "faces" / "11053.jpg"

t0 = time.perf_counter()
net, device = load_parsing_net(device="cpu")            # 强制 CPU，模拟服务器
t1 = time.perf_counter()

img = Image.open(str(IMG))
parsing = segment(net, img, device)
t2 = time.perf_counter()

parsing = segment(net, img, device)                     # 二次推理：稳定态耗时
t3 = time.perf_counter()

bgr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
mask = cv2.resize((parsing == 12).astype(np.float32),
                  (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_NEAREST)
out = apply_region_color(bgr, mask, [139, 77, 255])     # BGR ≈ #FF4D6D
t4 = time.perf_counter()

print("device          :", device)
print("模型加载         : %.2f s（服务化应提为进程级单例，只发生一次）" % (t1 - t0))
print("首次分割(含预热) : %.2f s" % (t2 - t1))
print("二次分割(稳定态) : %.2f s  ← 服务器单张体验值" % (t3 - t2))
print("Lab 换色        : %.3f s" % (t4 - t3))
print("单请求总耗时     : %.2f s（模型已驻留）" % (t3 - t2 + (t4 - t3)))
