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
    "blush": (1,),          # def 18 · 腮红：颧骨带派生自皮肤类(1)，实际掩码由 _blush_mask 生成
}
_DEFAULT_ALPHA = {"lip": 0.75, "foundation": 0.25, "eyeshadow": 0.45, "brow": 0.5, "blush": 0.45}


def _eyeshadow_mask(parsing, parts=(4, 5), size=0.5):
    """def 15v13/18c · 眼影掩码：眼皮皮肤带 + 眼眶内上缘，完全不触眼球；size∈[0,1] 控制范围。

    eye 类(4/5)只覆盖眼裂（眼球+眼睑内侧），真实眼影画在其上方的皮肤：
    lid 段 = 皮肤类(1) ∩ [eye_top - lid*h, eye_top)（眉眼间的眼皮，skin 与眉类互斥自动不越眉），
    rim 段 = eye 类 ∩ [eye_top, eye_top + rim*h)（睫毛根部着色）。
    眼球核心（rim 以下）零接触。
    size → lid = 0.35+0.40*size（小烟熏~大晕染）、rim = 0.10+0.10*size；size=0.5 = 定稿默认（0.55/0.15）。
    """
    lid = 0.35 + 0.40 * size
    rim = 0.10 + 0.10 * size
    eye = np.isin(parsing, parts).astype(np.uint8)
    skin = (parsing == 1).astype(np.uint8)
    out = np.zeros_like(eye)
    H = eye.shape[0]
    for x in np.where(eye.any(axis=0))[0]:
        col = np.where(eye[:, x])[0]
        top, bot = int(col.min()), int(col.max())
        h = max(1, bot - top)
        y0 = max(0, top - int(h * lid))
        y1 = min(H, top + int(h * rim))
        if y0 < min(y1, top):                      # 眼皮段：只要皮肤
            out[y0:min(y1, top), x] = skin[y0:min(y1, top), x]
        if y1 > top:                               # 眼眶内上缘段：只要眼睛类
            out[max(y0, top):y1, x] |= eye[max(y0, top):y1, x]
    return out


def _blush_mask(parsing, size=0.5):
    """def 18b/18c · 腮红掩码：颧骨椭圆软斑；size∈[0,1] 控制范围（0.5 = 定稿默认）。

    celebAMask 无"脸颊/颧骨"类，从现有类派生：
    - cheek = 皮肤(1) − (眉2,3/眼4,5/眼镜6/耳7,8/耳饰9/鼻10/口11/唇12,13/颈14)——五官零接触；
    - 尺度基准 = 半颊宽 half_w（颊掩码自身量出，自适应脸型，不用全图宽）；
    - 垂直：高斯分布（中心=眼唇距 48% 处），σ 随 size 增大；
    - 水平内：鼻翼侧淡出，满浓点随 size 外移（颊外半最浓）；
    - 水平外：逐行取颊掩码外缘渐出——留出发际线/脸轮廓空隙，留白随 size 收窄；
    - 浓度基准：内侧残留 0.35，满浓 1.0；柔边交给 apply_lip_color 的 feather（腮红分支 6.0）。
    size 映射（0.5 恰为 v18b 定稿值，向后兼容）：y_s=0.12+0.16s、inner=0.30−0.10s、
    full=0.53+0.18s、edge=0.23−0.10s。
    纯几何派生，无随机量，数值可复现。
    """
    y_c = 0.48
    y_s = 0.12 + 0.16 * size            # 垂直 σ：小→紧凑 / 大→晕染
    inner = 0.30 - 0.10 * size          # 鼻翼淡出起点
    full = 0.53 + 0.18 * size           # 满浓位置
    edge = 0.23 - 0.10 * size           # 外缘留白
    skin = (parsing == 1).astype(np.float32)
    ban = np.isin(parsing, [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
    cheek = skin * (~ban)
    eyes = np.isin(parsing, [4, 5])
    lips = np.isin(parsing, [12, 13])
    if not eyes.any() or not lips.any():
        return np.zeros(parsing.shape, np.float32)
    y_e = int(np.max(np.where(eyes.any(axis=1))[0]))     # 眼下缘
    y_l = int(np.min(np.where(lips.any(axis=1))[0]))     # 唇上缘
    if y_l <= y_e:
        return np.zeros(parsing.shape, np.float32)
    H, W = parsing.shape
    cols = np.where(cheek.any(axis=0))[0]
    if cols.size == 0:
        return np.zeros(parsing.shape, np.float32)
    cx = float(np.where(lips)[1].mean())                 # 唇质心 = 面部中线
    half_w = max(cx - float(cols.min()), float(cols.max()) - cx, 1.0)  # 半颊宽
    y_mid = y_e + (y_l - y_e) * y_c                      # 颧骨最高处（眼唇间中点偏上）
    sig = max(1.0, (y_l - y_e) * y_s)
    vy = np.exp(-((np.arange(H, dtype=np.float32) - y_mid) ** 2) / (2 * sig * sig))
    dx = np.abs(np.arange(W, dtype=np.float32)[None, :] - cx)
    wx_in = np.clip((dx - inner * half_w) / max(1e-6, (full - inner) * half_w), 0.0, 1.0)
    wx_in = 0.35 + 0.65 * wx_in                          # 鼻侧残留 0.35 → 颊外半 1.0
    wx_out = np.ones((H, W), np.float32)
    col_x = np.arange(W, dtype=np.float32)
    fade = edge * half_w
    for y in np.where(cheek.any(axis=1))[0]:             # 逐行：颊外缘 fade 内渐出
        xr = np.where(cheek[y])[0]
        if xr.size == 0:
            continue
        wx_out[y] = np.minimum(np.clip((col_x - float(xr.min())) / fade, 0.0, 1.0),
                               np.clip((float(xr.max()) - col_x) / fade, 0.0, 1.0))
    m = cheek * vy[:, None] * wx_in * wx_out
    m[m < 0.06] = 0.0                                    # 去零头：低于检出阈的渐变尾巴清零（防 JPEG 噪点）
    return m


def _apply_foundation(img_bgr, parsing, color_bgr, alpha, part=1, smooth=0.6, lum_ratio=0.5):
    """def 15v13 · 粉底 = 轻度磨皮(双边滤波匀肤) + Lab 全通道迁移。

    原 apply_lip_color 保留明度 L（唇纹纹理需要），粉底恰恰相反：
    - 磨皮：皮肤区纹理用双边滤波平滑版（smooth 比例混入），匀净底妆感；
    - 明度：Ls 向目标色明度迁移 lum_ratio=α*0.5（浅粉底提亮/深粉底加深，减半防假白）；
    - 色度：a/b 按 α 迁移；边缘羽化 sigma=3.0 比唇妆更柔。
    """
    img_f = img_bgr.astype(np.float32) / 255.0
    smooth_bgr = cv2.bilateralFilter(img_bgr, 9, 40, 40).astype(np.float32) / 255.0
    base = smooth_bgr * smooth + img_f * (1 - smooth)

    lab = cv2.cvtColor(base, cv2.COLOR_BGR2LAB)
    tar = np.array([[color_bgr]], dtype=np.float32) / 255.0
    tl, ta, tb = cv2.cvtColor(tar, cv2.COLOR_BGR2LAB)[0, 0]
    L, A, B = cv2.split(lab)
    lum = float(np.clip(alpha * lum_ratio, 0, 1))
    new_l = L * (1 - lum) + tl * lum
    new_a = A * (1 - alpha) + ta * alpha
    new_b = B * (1 - alpha) + tb * alpha
    changed = cv2.cvtColor(cv2.merge([new_l, new_a, new_b]), cv2.COLOR_LAB2BGR)

    mask = (parsing == part).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=3.0)[..., None]
    result = changed * mask + img_f * (1 - mask)
    return np.clip(result * 255, 0, 255).astype(np.uint8)


def run_tryon(image_bytes: bytes, hex_color: str, alpha: float = 0.75, parts: list = None) -> dict:
    """def 12a/15 · 试妆主函数：照片字节 + hex 进，原图/上妆图 base64 出。

    def 15 · 多部位聚合：parts = [{"region": "lip|foundation|eyeshadow|brow|blush",
    "hex": "#xxx", "alpha": 0.x, "size": 0.x(可选,腮红/眼影范围,默认0.5)}, ...]；
    None/缺省 = 单唇模式（向后兼容 def 12）。
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
        size = spec.get("size", 0.5)         # def 18c · 范围（腮红/眼影用）；其他部位忽略该字段
        if not isinstance(size, (int, float)) or isinstance(size, bool) or not (0 <= float(size) <= 1):
            return {"ok": False, "tool": tool,
                    "error": f"{region} size 须在 [0,1] 区间，收到 {size!r}", "results": {}}
        norm_specs.append({"region": region, "hex": hex_r, "alpha": float(a), "size": float(size)})

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
        if region == "eyeshadow":            # def 15v13 · 眼皮皮肤带+睫毛根，眼球零接触；size 控范围
            out_img = apply_lip_color(out_img, p, 4, hex2bgr(spec["hex"]),
                                      alpha=spec["alpha"], gloss=0.0, mask=_eyeshadow_mask(p, size=spec["size"]))
            continue
        if region == "foundation":           # def 15v13 · 粉底=磨皮+明度/色度全迁移
            out_img = _apply_foundation(out_img, p, hex2bgr(spec["hex"]), spec["alpha"])
            continue
        if region == "blush":                # def 18 · 颧骨带+水平渐变，feather=6 大羽化柔边，无高光；
            out_img = apply_lip_color(out_img, p, 1, hex2bgr(spec["hex"]),  # α×1.6 过驱：腮红目标色与肤色
                                      alpha=min(1.0, spec["alpha"] * 1.6), gloss=0.0,  # 本征色差小，
                                      feather=6.0, mask=_blush_mask(p, size=spec["size"]))  # 不放大则几乎不可见
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


def run_face_profile(image_bytes):
    """def 43 · 人脸属性档案：白平衡校正 + BiSeNet 解析 → 五官取色结构化数据。

    复用 _get_net() 单例（与试妆共用同一次模型加载）；解析用白平衡校正图，
    肤色取色按 YCbCr 肤色域得分在原图/校正图间择优（防白皮拍成黄皮/越校越黄）。
    输出纯数据（无图），前端拿去渲染档案面板并组装 AI 推荐上下文——省 token：
    AI 不看图、不反问，直接基于事实推荐。
    """
    tool = "face_profile"
    if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
        return {"ok": False, "tool": tool, "error": "未收到图片数据", "results": {}}
    if len(image_bytes) > 10 * 1024 * 1024:
        return {"ok": False, "tool": tool, "error": "图片超过 10MB 限制", "results": {}}
    img_bgr = cv2.imdecode(np.frombuffer(bytes(image_bytes), np.uint8), cv2.IMREAD_COLOR)
    if img_bgr is None:
        return {"ok": False, "tool": tool, "error": "无法解码图片，请上传 jpg/png 格式", "results": {}}
    try:
        from PIL import Image
        from lipstick.tryon import segment
        from face_profile import analyze          # beauty/ 已在模块头插入 sys.path
        net, device = _get_net()
        parsing = segment(net, Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)), device)
        profile = analyze(img_bgr, parsing)
    except FileNotFoundError as e:
        return {"ok": False, "tool": tool, "error": f"分割模型权重缺失: {e}", "results": {}}
    except Exception as e:
        return {"ok": False, "tool": tool, "error": f"人脸解析失败: {e}", "results": {}}
    H, W = img_bgr.shape[:2]
    return {"ok": True, "tool": tool,
            "query": {"wh": [W, H], "device": device},
            "results": {"profile": profile},
            "error": None}