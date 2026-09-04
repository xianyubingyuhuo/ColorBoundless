# -*- coding: utf-8 -*-
"""
regen_lab.py
============
base_palette lab 回填脚本（配套 audit_lab.py，决策卡 D-02）

- 问题：red/purple_base.json 的 lab 字段为 AI 手写值，8/8 审计不合格
  （偏差 0.5~11.5，定性对、定量错，无系统方向 → 排除公式变体）
- 原则：数学字段必须可复算——修复本身也要可复算（脚本回填，不手改数字）
- 波及面：零消费者（2026-09-04 grep 确认，仅 README 提及 + audit_lab.py）
- 防回归：回填后 audit_lab.py 应 8/8 通过；此后凡改 base_palette 数据先跑审计
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))              # cv 包（lipstick/__init__ → tryon 需要）
sys.path.insert(0, str(PROJECT_ROOT / "beauty"))   # lipstick 包

from lipstick.shade_library import hex2lab

BASE_DIR = PROJECT_ROOT / "data" / "knowledge_base" / "base_palette"
TOLERANCE = 0.5  # 与 audit_lab.py 同一判定标准，两把尺子必须一样长

for name in ["red_base.json", "purple_base.json"]:
    path = BASE_DIR / name
    entries = json.load(path.open(encoding="utf-8"))
    changed = 0
    for e in entries:
        # float(): np.float64 进不了 json（TypeError）；round(…,1) 保持原文件 1 位小数格式
        true_lab = [round(float(x), 1) for x in hex2lab(e["hex"])]
        old = e["lab"]
        if any(abs(t - s) > TOLERANCE for t, s in zip(true_lab, old)):
            e["lab"] = true_lab
            changed += 1
            print(f"  回填 {e['palette_id']} {e['hex']}: {old} → {true_lab}")
        else:
            print(f"  跳过 {e['palette_id']} {e['hex']}: 偏差在容差内")
    # ensure_ascii=False 保中文不转义；indent=2 与原格式一致，git diff 干净
    with path.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"{name}: 回填 {changed}/{len(entries)} 条\n")
