# -*- coding: utf-8 -*-
"""def 12a · 试妆服务层：算法层零件 + 服务级模型单例。

三个设计决策：
1. 不直接调算法层 tryon()——它每次调用都重新加载 BiSeNet（函数体内建模型），
   HTTP 场景每试一次卡 10s+。这里 lru_cache 单例，模型只加载一次。
2. torch/cv2/PIL/cv.face_parsing 全部延迟导入（函数体内）——main.py 启动
   不被重依赖链拖住；试妆模块没被调用时，这些库一个字节都不加载。
3. 不进 function calling 注册表——试妆是用户的主动操作（上传照片），
   不是大脑的对话决策；走 HTTP 直连，输出 base64 内嵌 JSON（前端直接 <img>）。
铁律照旧：五件套 JSON、错误不穿透、hex 复用工具①的门卫 normalize_hex。
"""
import base64
import functools
import sys
from pathlib import Path

import cv2
import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "beauty")):   # cv.face_parsing 要 root，lipstick 要 beauty/
    if _p not in sys.path:
        sys.path.insert(0, _p)


@functools.lru_cache(maxsize=1)
def _get_net():
    """BiSeNet 单例（首次调用拉起 torch 全链，约 10~20s；之后毫秒级取缓存）。"""
    import torch
    from cv.face_parsing import BiSeNet
    from lipstick.tryon import DEFAULT_WEIGHTS
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = BiSeNet(n_classes=19)
    net.load_state_dict(torch.load(DEFAULT_WEIGHTS, map_location=device))
    net.to(device).eval()
    return net, device


def run_tryon(image_bytes: bytes, hex_color: str, alpha: float = 0.75) -> dict:
    """def 12a · 试妆主函数：照片字节 + hex 进，原图/上妆图 base64 出。

    成功: {"ok": true,  "tool": "tryon",
           "query":  {"hex", "alpha", "device", "wh"},
           "results": {"original_b64", "makeup_b64"},   # 前端 <img src=data:...>
           "error": null}
    失败: {"ok": false, "tool": "tryon", "error": "人话原因", "results": {}}
    """
    tool = "tryon"

    # 1) hex 清洗：复用工具①门卫（不重写规则）
    from agents.tools.search_shade import normalize_hex
    try:
        hex_std = normalize_hex(hex_color)
    except ValueError as e:
        return {"ok": False, "tool": tool, "error": str(e), "results": {}}

    # 2) alpha 卫生检查（bool 是 int 子类，照旧排除）
    if not isinstance(alpha, (int, float)) or isinstance(alpha, bool) or not (0 < float(alpha) <= 1):
        return {"ok": False, "tool": tool, "error": f"alpha 须在 (0,1] 区间，收到 {alpha!r}", "results": {}}
    alpha = float(alpha)

    # 3) 图片解码（不支持/损坏 → 人话报错）
    img_bgr = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img_bgr is None:
        return {"ok": False, "tool": tool, "error": "无法解码图片，请上传 jpg/png 格式", "results": {}}

    # 4) 分割 + 上妆（算法层零件：segment / apply_lip_color）
    from PIL import Image
    from lipstick.tryon import segment, apply_lip_color, hex2bgr
    try:
        net, device = _get_net()
        img_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
        parsing = segment(net, img_pil, device)
    except FileNotFoundError as e:
        return {"ok": False, "tool": tool, "error": f"分割模型权重缺失: {e}", "results": {}}
    except Exception as e:
        return {"ok": False, "tool": tool, "error": f"人像分割失败: {e}", "results": {}}

    H, W = img_bgr.shape[:2]
    p = cv2.resize(parsing, (W, H), interpolation=cv2.INTER_NEAREST)
    out_img = img_bgr.copy()
    for part in (12, 13):                    # 上唇 + 下唇（算法层定稿的 part 编号）
        out_img = apply_lip_color(out_img, p, part, hex2bgr(hex_std), alpha=alpha)

    # 5) base64 输出（np→字节→base64，json 安全）
    ok1, buf1 = cv2.imencode(".jpg", img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    ok2, buf2 = cv2.imencode(".jpg", out_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not (ok1 and ok2):
        return {"ok": False, "tool": tool, "error": "结果图编码失败", "results": {}}

    return {"ok": True, "tool": tool,
            "query": {"hex": hex_std, "alpha": alpha, "device": device, "wh": [W, H]},
            "results": {"original_b64": base64.b64encode(buf1.tobytes()).decode("ascii"),
                        "makeup_b64": base64.b64encode(buf2.tobytes()).decode("ascii")},
            "error": None}