# -*- coding: utf-8 -*-
"""临时检查：官方色号库结构（用后即删）"""
import importlib.util
from pathlib import Path

p = Path("beauty/lipstick/shade_library.py").resolve()
spec = importlib.util.spec_from_file_location("sl", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

print("SHADES 数量:", len(m.SHADES))
import json
print("首条字段:", json.dumps(m.SHADES[0], ensure_ascii=False)[:300])
lab = m.hex2lab("FF4D6D")
print("hex2lab:", [round(float(x), 2) for x in lab])
print("search 函数:", [n for n in dir(m) if not n.startswith("_")])
