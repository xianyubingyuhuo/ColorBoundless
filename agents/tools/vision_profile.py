# -*- coding: utf-8 -*-
"""工具⑤ get_vision_profile——大脑读取用户色觉档案的通道（def 17 · AI 总结铺路）。

职责：把 cvd_exam 的最新测评档案以五件套交给大脑，AI 据此组织个性化话术
（校色建议 / 用色结论 / 引导下一步），判定数据本身全部由 cvd_test 规则引擎产出。

模块单例警示（2026-09-13 修复）：必须以 `from cvd_exam import ...` 引入——与
main.py 的模块名一致才能共享同一个 _PROFILE 实例；若用 `app.backend.cvd_exam`
包路径 import 会产生第二个模块实例，档案永远读不到（已踩坑）。
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "app" / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cvd_exam import get_profile


def get_vision_profile_tool() -> dict:
    """读取最新色觉档案（cvd_type / severity / 三维阈值 / 置信度 / 证据链）。"""
    try:
        out = get_profile()
        if not out.get("ok"):
            return {"ok": False, "tool": "get_vision_profile_tool",
                    "error": "用户尚未完成色盲测评——可引导 TA 去 cvd 页做测评（约 12 题）",
                    "results": {}}
        return out
    except Exception as exc:
        return {"ok": False, "tool": "get_vision_profile_tool",
                "error": f"档案读取异常: {exc}", "results": {}}
