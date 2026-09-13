# -*- coding: utf-8 -*-
"""def 17d · GB/T 15608 命名数据生成器（纯 GB 命名，职责单一）。

生成 data/shades/gb_names_16.json：
    16³ = 4096 采样点 × {hex, rgb, gb_label, gb_cn}
职责分离（用户 2026-09-13 定稿）：
    本文件只生成 **GB 命名**；官方色号匹配由 coverage16 端点运行时从
    shades.json 计算——官方库扩充后匹配自动跟随，无需重跑本脚本。
用法：
    .venv/Scripts/python.exe scripts/generate_gb_names_16.py
命名规则与修正记录见 agents/tools/search_shade.py 的 gb_color_name。
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "backend"))

from agents.tools.search_shade import gb_color_name   # GB 命名（HSV 色调 + 修饰互斥）
from cvd_test.color_diff import srgb2lab              # 与 shade_library.hex2lab 同公式


def hex2lab(hx: str) -> list:
    """hex → CIELAB（与 shade_library.hex2lab 同公式：sRGB→Lab）"""
    return list(srgb2lab([int(hx[i:i + 2], 16) for i in (0, 2, 4)]))

OUT = ROOT / "data" / "shades" / "gb_names_16.json"
LEVELS = [round(i * 255 / 15) for i in range(16)]


def main():
    items = []
    t0 = time.time()
    for r in LEVELS:
        for g in LEVELS:
            for b in LEVELS:
                hx = f"{r:02X}{g:02X}{b:02X}"
                gb = gb_color_name((r, g, b), list(hex2lab(hx)))
                items.append({"hex": hx, "rgb": [r, g, b],
                              "gb_label": gb["label"], "gb_cn": gb["cn"]})
    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sampling": "16x16x16=4096",
        "count": len(items),
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {OUT.name}（{len(items)} 色，耗时 {round(time.time() - t0, 1)}s）")
    for probe in ("000000", "000088", "FF1111", "FFFFFF"):
        w = next(it for it in items if it["hex"] == probe)
        print(f"  #{probe}: {w['gb_cn']}（{w['gb_label']}）")


if __name__ == "__main__":
    main()
