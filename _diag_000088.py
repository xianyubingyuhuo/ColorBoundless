# -*- coding: utf-8 -*-
"""临时诊断：#000088 的官方库匹配（用后即删）"""
import importlib.util
import math
from pathlib import Path

import numpy as np

p = Path("beauty/lipstick/shade_library.py").resolve()
spec = importlib.util.spec_from_file_location("sl", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

q_hex = "000088"
q_lab = np.array(m.hex2lab(q_hex))
print(f"查询 {q_hex} Lab = {q_lab.round(2)}")

rows = []
for s in m.SHADES:
    s_lab = np.array(m.hex2lab(s["hex"]))
    dE00 = float(m.ciede2000(q_lab, s_lab))
    eu = float(np.sqrt(((q_lab - s_lab) ** 2).sum()))
    rows.append((dE00, eu, s["hex"], s["name"], s_lab.round(1).tolist()))

rows.sort()
print("\n按 ΔE00 升序（前 5）:")
for dE00, eu, hex_, name, lab in rows[:5]:
    print(f"  dE00={dE00:6.2f} 欧氏={eu:6.2f}  {hex_} {name}  Lab={lab}")

print("\n按欧氏升序（前 5）:")
for dE00, eu, hex_, name, lab in sorted(rows, key=lambda r: r[1])[:5]:
    print(f"  欧氏={eu:6.2f} dE00={dE00:6.2f}  {hex_} {name}")

# 对照 coverage16 的实现（欧氏 argmin）
off_lab = np.array([np.array(m.hex2lab(s["hex"])) for s in m.SHADES])
d = ((q_lab[None, :] - off_lab) ** 2).sum(-1)
k = int(d.argmin())
print(f"\ncoverage16 的 argmin 选中: {m.SHADES[k]['hex']} {m.SHADES[k]['name']}")

# GB 命名诊断
a, b = q_lab[1], q_lab[2]
print(f"\nLab 色相角 = {math.degrees(math.atan2(b, a)) % 360:.1f}°（我的分区映射到红紫）")
hsv_v = max(q_hex[i:i+2] for i in (0, 2, 4))
print("MAX 通道:", hsv_v)
