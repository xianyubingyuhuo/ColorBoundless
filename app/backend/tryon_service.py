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

from agents.tools.search_shade import normalize_hex   # def 15 · hex 门卫复用（轻依赖，不拉 torch）

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


_REGION_PARTS = {          # def 15 · region → BiSeNet 解析类（celebAMask 19 类编号）
    "lip": (12, 13),        # 上唇 + 下唇
    "foundation": (1,),     # 粉底：皮肤（全脸均匀，低 alpha 防假白）
    "eyeshadow": (4, 5),    # 眼影：左眼 + 右眼
    "brow": (2, 3),         # 眉：染眉/加深（预留）
}
_DEFAULT_ALPHA = {"lip": 0.75, "foundation": 0.25, "eyeshadow": 0.45, "brow": 0.5}


def _upper_lid_mask(parsing, parts=(4, 5), band=0.45):
    """def 15v10 · 眼影掩码：每列取眼睛区域的顶部带（上眼睑），避开眼球/下眼睑。

    celebAMask 4/5 是整只眼（含眼球），直接混色会把虹膜染成眼影色；
    逐列取顶部 band 比例近似"只涂眼皮"。
    """
    mask = np.isin(parsing, parts).astype(np.uint8)
    out = np.zeros_like(mask)
    for x in np.where(mask.any(axis=0))[0]:
        col = np.where(mask[:, x])[0]
        top, bot = int(col.min()), int(col.max())
        out[top:top + max(1, int((bot - top) * band)), x] = 1
    return out


def run_tryon(image_bytes: bytes, hex_color: str, alpha: float = 0.75, parts: list = None) -> dict:
    """def 12a/15 · 试妆主函数：照片字节 + hex 进，原图/上妆图 base64 出。

    def 15 · 多部位聚合：parts = [{"region": "lip|foundation|eyeshadow|brow",
    "hex": "#xxx", "alpha": 0.x}, ...]；None/缺省 = 单唇模式（向后兼容 def 12）。
    未指定 alpha 的部位用部位默认值（foundation 低 alpha 防假白面具）。
    apply_lip_color 本质是"任意部件掩码 + 颜色 + alpha 的混合上色"，换 part 即换部位。

    成功: {"ok": true,  "tool": "tryon",
           "query":  {"hex", "alpha", "device", "wh", "applied": [部位明细]},
           "results": {"original_b64", "makeup_b64"},   # 前端 <img src=data:...>
           "error": null}
    失败: {"ok": false, "tool": "tryon", "error": "人话原因", "results": {}}
    """
    tool = "tryon"

    # 0) parts 规范化（def 15）：None → 单唇向后兼容；非法部位/hex/alpha 立即报错
    specs = parts if isinstance(parts, list) and parts else [
        {"region": "lip", "hex": hex_color, "alpha": alpha}]
    norm_specs = []
    for spec in specs:
        if not isinstance(spec, dict):
            return {"ok": False, "tool": tool, "error": "parts 每项须为对象", "results": {}}
        region = str(spec.get("region", "lip")).lower()
        if region not in _REGION_PARTS:
            return {"ok": False, "tool": tool,
                    "error": f"未知部位: {region}（可用: {', '.join(_REGION_PARTS)}）", "results": {}}
        try:
            hex_r = normalize_hex(spec.get("hex", hex_color))
        except ValueError as e:
            return {"ok": False, "tool": tool, "error": f"{region} 色值: {e}", "results": {}}
        a = spec.get("alpha", _DEFAULT_ALPHA[region])
        if not isinstance(a, (int, float)) or isinstance(a, bool) or not (0 < float(a) <= 1):
            return {"ok": False, "tool": tool,
                    "error": f"{region} alpha 须在 (0,1] 区间，收到 {a!r}", "results": {}}
        norm_specs.append({"region": region, "hex": hex_r, "alpha": float(a)})

    # 1) 主 hex 清洗：复用工具①门卫（不重写规则）
    try:
        hex_std = normalize_hex(hex_color)
    except ValueError as e:
        return {"ok": False, "tool": tool, "error": str(e), "results": {}}

    # 2) alpha 卫生检查（主 alpha；bool 是 int 子类，照旧排除）
    if not isinstance(alpha, (int, float)) or isinstance(alpha, bool) or not (0 < float(alpha) <= 1):
        return {"ok": False, "tool": tool, "error": f"alpha 须在 (0,1] 区间，收到 {alpha!r}", "results": {}}
    alpha = float(alpha)

    # 3) 图片解码（不支持/损坏 → 人话报错）
    img_bgr = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img_bgr is None:
        return {"ok": False, "tool": tool, "error": "无法解码图片，请上传 jpg/png 格式", "results": {}}

    # 4) 分割 + 多部位聚合渲染（算法层零件：segment / apply_lip_color——任意 part 掩码混合）
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
    for spec in norm_specs:                  # def 15 · 聚合渲染：逐部位掩码混合
        region = spec["region"]
        if region == "eyeshadow":            # def 15v10 · 只染上眼睑带，避开眼球
            out_img = apply_lip_color(out_img, p, 4, hex2bgr(spec["hex"]),
                                      alpha=spec["alpha"], gloss=0.0, mask=_upper_lid_mask(p))
            continue
        gloss = 0.3 if region == "lip" else 0.0   # 唇釉高光仅属唇妆；粉底/眼影/眉不上反光
        for part in _REGION_PARTS[region]:
            out_img = apply_lip_color(out_img, p, part, hex2bgr(spec["hex"]),
                                      alpha=spec["alpha"], gloss=gloss)

    # 5) base64 输出（np→字节→base64，json 安全）
    ok1, buf1 = cv2.imencode(".jpg", img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    ok2, buf2 = cv2.imencode(".jpg", out_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not (ok1 and ok2):
        return {"ok": False, "tool": tool, "error": "结果图编码失败", "results": {}}

    return {"ok": True, "tool": tool,
            "query": {"hex": hex_std, "alpha": alpha, "device": device, "wh": [W, H],
                      "applied": norm_specs},
            "results": {"original_b64": base64.b64encode(buf1.tobytes()).decode("ascii"),
                        "makeup_b64": base64.b64encode(buf2.tobytes()).decode("ascii")},
            "error": None}