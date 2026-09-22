# -*- coding: utf-8 -*-
"""def 43 · face_profile 测试：白平衡单测 + 端到端解析 + 人造偏色鲁棒对照。

运行（项目根）：python scripts/testing_scripts/test_face_profile.py
"""
import json
import math
import os
import sys

import cv2
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "beauty"))

from beauty.face_profile import white_balance, analyze          # noqa: E402
from lipstick.tryon import segment, DEFAULT_WEIGHTS             # noqa: E402


def test_white_balance():
    """合成偏色图 → 校正后应回到原白（ΔRGB ≤ 3）；gains 方向正确。"""
    base = np.full((64, 64, 3), 200.0, np.float32)             # 中性灰
    shifted = np.clip(base * np.array([0.90, 1.0, 1.12]), 0, 255).astype(np.uint8)  # 偏红黄
    wb, gains = white_balance(shifted)
    err = abs(wb.mean() - 200.0)
    assert err <= 3.0, f"白平衡后均值偏差过大: {err:.2f}"
    assert gains[2] < 1.0 < gains[0], f"gains 方向错: {gains}"  # 红超标→R gain<1，B 不足→B gain>1
    print(f"[1] 白平衡单测通过（校正后均值 {wb.mean():.1f}，目标 200；gains BGR={np.round(gains,3)}）")


def _run(tag, img_bgr, net, device):
    from PIL import Image
    parsing = segment(net, Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)), device)
    out = analyze(img_bgr, parsing)
    print(f"\n===== {tag} =====")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def main():
    test_white_balance()

    import torch
    from cv.face_parsing import BiSeNet
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = BiSeNet(n_classes=19)
    net.load_state_dict(torch.load(DEFAULT_WEIGHTS, map_location=device))
    net.to(device).eval()

    photo = os.path.join(_ROOT, "data", "faces", "11053.jpg")
    img = cv2.imdecode(np.fromfile(photo, np.uint8), cv2.IMREAD_COLOR)   # 中文路径 imread 会失败（项目已知坑）
    assert img is not None, "测试照片缺失: " + photo

    ref = _run("原图（基准）", img, net, device)

    # 人造偏色：整体偏黄（模拟白皮拍成黄皮）→ 期望校正后档位/底调与基准一致或接近
    warm = np.clip(img.astype(np.float32) * np.array([0.90, 0.98, 1.14]), 0, 255).astype(np.uint8)
    got = _run("人造偏黄图（应自动校正回基准附近）", warm, net, device)

    if ref["skin"].get("status") == "ok" and got["skin"].get("status") == "ok":
        def _dE(h1, h2):
            v1 = np.array([int(h1[i:i+2], 16) for i in (0, 2, 4)], np.float32)
            v2 = np.array([int(h2[i:i+2], 16) for i in (0, 2, 4)], np.float32)
            return float(np.linalg.norm(v1 - v2))
        d = _dE(ref["skin"]["hex"], got["skin"]["hex"])
        print(f"\n[2] 偏黄图 vs 基准 肤色 RGB 距离 = {d:.1f}（档位 {got['skin']['level']} vs {ref['skin']['level']}，"
              f"底调 {got['skin']['undertone']} vs {ref['skin']['undertone']}，chosen={got['correction']['chosen']}）")
    print("\n全部测试完成")


if __name__ == "__main__":
    main()
