# -*- coding: utf-8 -*-
"""def 17d · 全色域覆盖数据生成器（数据外置：命名与匹配结果进 JSON，代码不内联）。

生成 data/shades/color_coverage_16.json：
    16³ = 4096 采样点 × [hex, rgb, gb_label, gb_cn, official_hex, official_name, dE, has_official]
用法：
    .venv/Scripts/python.exe scripts/generate_color_coverage.py
色号库（shades.json）扩充后重跑本脚本即可刷新覆盖数据（覆盖率随库容提升）。

算法修正记录（2026-09-13，用户报错 #000088 → 樱花粉）：
    官方匹配从 Lab 欧氏 argmin 改为 **ΔE00 全量取最小**——深色区欧氏与 ΔE00
    严重背离（欧氏最近的樱花粉 dE00=44，而真最近干枯玫瑰 dE00=32）。
    GB 命名色调改用 HSV 色相角 + 修饰语互斥（详见 agents/tools/search_shade.py）。
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "backend"))

import importlib.util

_core_spec = importlib.util.spec_from_file_location(
    "shade_library_core", ROOT / "beauty" / "lipstick" / "shade_library.py")
_core = importlib.util.module_from_spec(_core_spec)
_core_spec.loader.exec_module(_core)

from agents.tools.search_shade import gb_color_name   # 修好的 GB 命名（HSV 色调 + 修饰互斥）

OUT = ROOT / "data" / "shades" / "color_coverage_16.json"
LEVELS = [round(i * 255 / 15) for i in range(16)]


def main():
    shades = _core.SHADES
    print(f"官方色号库：{len(shades)} 条")
    off_lab = {s["hex"]: list(_core.hex2lab(s["hex"])) for s in shades}

    items, hits = [], 0
    t0 = time.time()
    for r in LEVELS:
        for g in LEVELS:
            for b in LEVELS:
                hx = f"{r:02X}{g:02X}{b:02X}"
                lab = list(_core.hex2lab(hx))
                # ΔE00 全量取最小（官方库 20 条 × 4096 点 = 81920 次，纯 Python 数秒）
                best_k, best_d = 0, 1e9
                for k, s in enumerate(shades):
                    dE = float(_core.ciede2000(lab, off_lab[s["hex"]]))
                    if dE < best_d:
                        best_k, best_d = k, dE
                s = shades[best_k]
                gb = gb_color_name((r, g, b), lab)
                label, cn = gb["label"], gb["cn"]
                has = best_d <= 1.0
                hits += int(has)
                items.append({"hex": hx, "rgb": [r, g, b],
                              "gb_label": label, "gb_cn": cn,
                              "official_hex": s["hex"], "official_name": s["name"],
                              "dE": round(best_d, 2), "has_official": has})
    elapsed = round(time.time() - t0, 1)

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sampling": "16x16x16=4096",
        "official_shades": len(shades),
        "threshold_dE": 1.0,
        "stats": {"total": len(items), "hits": hits,
                  "miss": len(items) - hits,
                  "coverage_pct": round(100.0 * hits / len(items), 2)},
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")   # 垂直换行，可读可 diff
    print(f"生成 {OUT.name}（{len(items)} 色，耗时 {elapsed}s，覆盖率 {out['stats']['coverage_pct']}%）")

    # 抽查关键样本（均为 16³ 网格内色值）
    for probe in ("000000", "000088", "FF1111", "FFFFFF"):
        w = next(it for it in items if it["hex"] == probe)
        print(f"  #{probe}: GB={w['gb_cn']}({w['gb_label']}) → 官方 {w['official_name']}({w['official_hex']}) dE={w['dE']} has={w['has_official']}")


if __name__ == "__main__":
    main()
