# -*- coding: utf-8 -*-
"""工具① search_shade —— 色号检索（agent 的手，选色主链路第一站）

输入输出约定（呼应 agents/prompt.py 的 OUTPUT_CONTRACT）：
    结构化 JSON 进、结构化 JSON 出；数字永远由代码算，LLM 只引用不心算。
依赖方向：
    本模块只依赖 beauty/lipstick/shade_library（算法层），算法层不知道 agent 存在。
"""
import importlib.util
import re
from pathlib import Path

# 6 位 hex 的合法形态：0-9 / a-f / A-F，恰好 6 位
_HEX6 = re.compile(r"^[0-9a-fA-F]{6}$")


def normalize_hex(raw: str) -> str:
    """def 1 · 输入清洗：把随手写的色值统一成内部标准 —— 6 位大写、无 #。

    接受 "#FF4D6D" / "ff4d6d" / "F46"（CSS 三位缩写）/ " #f46 " 之类，
    统一输出 "FF4D6D" 这种内部标准形（shade_library 内部就是 lstrip('#') 后使用）。
    不合格式抛 ValueError，错误信息说人话——上层工具函数负责把它转成 JSON error 字段。
    """
    if not isinstance(raw, str):
        raise ValueError(f"色值必须是字符串，收到 {type(raw).__name__}")
    s = raw.strip().lstrip("#")
    if len(s) == 3:                      # CSS 三位缩写：f46 -> ff4466（每位翻倍）
        s = "".join(ch * 2 for ch in s)
    if not _HEX6.fullmatch(s):
        raise ValueError(f"无效色值: {raw!r}（清洗后 {s!r}，需要 3 或 6 位 hex 字符）")
    return s.upper()


# ---------------------------------------------------------------------------
# 算法层接线：importlib 按路径直载 shade_library.py（cwd 双目录实验的结论落地）
# 为什么不走包导入？from lipstick... 必先执行 lipstick/__init__ -> tryon.py
# -> import torch/cv2 —— 工具①只想算色差，不该背着 BiSeNet 起步。
# 直载只执行 shade_library.py 本体：模块级 _load_shades() 读 shades.json，
# 用 Path(__file__).parents[2] 锚定正本，与 sys.path / cwd 全解耦。
# ---------------------------------------------------------------------------
_CORE_PATH = Path(__file__).resolve().parents[2] / "beauty" / "lipstick" / "shade_library.py"
_core_spec = importlib.util.spec_from_file_location("shade_library_core", _CORE_PATH)
_core = importlib.util.module_from_spec(_core_spec)
_core_spec.loader.exec_module(_core)


def search_shade_tool(raw_hex: str, top_k: int = 3) -> dict:
    """def 2 · 工具① 主函数：脏 hex 进，结构化 JSON 出（LLM 可直接引用）。

    成功: {"ok": true,  "tool": "search_shade",
           "query":  {"hex": "FF4D6D", "lab": [L, a, b]},
           "results": [shades.json 条目 + dE，按 CIEDE2000 升序],
           "error": null}
    失败: {"ok": false, "error": "人话原因", "results": []}
    错误也是 JSON——绝不向 agent / HTTP 层抛异常穿透，
    LLM 拿到 error 字段才知道怎么向用户解释（呼应 prompt.py 输出契约）。
    """
    tool = "search_shade"

    # 1) 输入清洗（def 1 的门卫），失败 -> 错误 JSON
    try:
        hex_std = normalize_hex(raw_hex)
    except ValueError as e:
        return {"ok": False, "tool": tool, "error": str(e), "results": []}

    # 2) top_k 卫生检查：bool 是 int 的子类要排除；范围钳到 [1, 库容量]
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        return {"ok": False, "tool": tool,
                "error": f"top_k 必须是整数，收到 {top_k!r}", "results": []}
    k = max(1, min(top_k, len(_core.SHADES)))

    # 3) 调算法层：CIEDE2000 全库比对，数字永远由代码算
    try:
        rows = _core.search_shade(hex_std, top_k=k)
    except Exception as e:               # 算法层意外错误同样不穿透
        return {"ok": False, "tool": tool, "error": f"检索失败: {e}", "results": []}

    # 4) 组装契约：query 里的 lab 是代码算的物理量，LLM 只准引用不准心算
    lab = [round(float(x), 2) for x in _core.hex2lab(hex_std)]
    return {"ok": True, "tool": tool,
            "query": {"hex": hex_std, "lab": lab},
            "results": rows,
            "error": None}
