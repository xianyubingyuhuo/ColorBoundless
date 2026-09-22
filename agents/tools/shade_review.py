# -*- coding: utf-8 -*-
"""工具⑦ shade_review——大脑的「选色社会视角守门」通道（def 27）。

用户问「这个颜色适不适合出门 / 别人会怎么看 / 要不要换个正常的」时，
大脑调用本工具拿到代码计算的判定（主流性 + 正常人视角色相描述 +
社会等效色 + 在售主流替代），AI 只引用结果组织话术，不心算颜色。

模块单例警示（与 vision_profile.py 同源）：必须以顶层名 import
（`from shade_review import ...`），与 main.py 共享同一实例。
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "app" / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from shade_review import shade_review


def shade_review_tool(raw_hex: str, region: str) -> dict:
    """选色社会视角守门（主流性 / 别人看到的 / 社会等效色 / 在售替代推荐）。"""
    try:
        return shade_review(raw_hex, region)
    except Exception as exc:
        return {"ok": False, "tool": "shade_review_tool",
                "error": f"守门判定异常: {exc}", "results": {}}
