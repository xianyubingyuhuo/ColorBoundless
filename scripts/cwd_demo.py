# -*- coding: utf-8 -*-
"""
cwd 双目录实验 —— 避坑注释 #3 的实弹版（教学脚本，无副作用，只读）

同一个脚本从两个不同目录运行，回答三个问题：
  Q1: os.getcwd() / __file__ / sys.path[0]，哪个随 cd 变？
  Q2: 为什么导入 shade_library 要把 项目根 + beauty/ 两个都插进 sys.path？
  Q3: 数据正本 shades.json 为什么永远加载得到？（shade_library 内部的锚定手法）

运行方式（venv python 加 -X utf8，各跑一次对比输出）：
  cd <项目根>            <venv>python -X utf8 scripts\\cwd_demo.py
  cd <项目根>\\beauty     <venv>python -X utf8 ..\\scripts\\cwd_demo.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # 避坑 #1：GBK 打不出 emoji
import os
from pathlib import Path

SEP = "=" * 64
print(SEP)
print("cwd_demo.py —— 同一个脚本，两种 cd，看三个『位置』谁在漂")
print(SEP)

# ---------- Q1: 三个位置，谁随 cd 变 ----------
print("[1] os.getcwd()                =", os.getcwd(), "        <- 随 cd 漂")
print("[2] __file__（解释器收到的原文） =", __file__)
print("[3] Path(__file__).resolve()   =", Path(__file__).resolve(), " <- resolve 后不漂")
print("[4] sys.path[0]（import 起点）  =", sys.path[0], " <- 是脚本所在目录，不是你 cd 的地方")

ROOT = Path(__file__).resolve().parents[1]      # scripts/ 的上一级 = 项目根
BEAUTY = ROOT / "beauty"
print("[5] 由 __file__ 反推：ROOT =", ROOT, "（与 cd 无关）")


def try_import(stmt: str) -> bool:
    """教学用：exec 一条 import 语句并如实报告成败（正常业务代码别用 exec）。"""
    try:
        exec(stmt, globals())
        print(f"    OK  {stmt}")
        return True
    except Exception as e:
        print(f"    XX  {stmt}")
        print(f"        -> {type(e).__name__}: {e}")
        return False


# ---------- Q2: 三种导入姿势，sys.path 动刀前后对比 ----------
STMTS = ["import shade_library",
         "from lipstick import shade_library",
         "from beauty.lipstick import shade_library"]

print("-" * 64)
print("[6] 初始 sys.path（= scripts/ + 标准库，无项目根、无 beauty/）:")
for s in STMTS:
    try_import(s)

sys.path.insert(0, str(BEAUTY))
print(f"[7] sys.path.insert(0, beauty/) 之后:")
for s in STMTS:
    try_import(s)

sys.path.insert(0, str(ROOT))
print(f"[8] 再 sys.path.insert(0, 项目根) 之后:")
for s in STMTS:
    try_import(s)

print("    >> 为什么两个目录都要插？一条导入链横跨两层：")
print("       lipstick/ 在 beauty/ 下            -> 需要 beauty/   (import lipstick)")
print("       lipstick/__init__ -> tryon.py")
print("         -> from cv.face_parsing import BiSeNet, cv/ 在项目根下 -> 需要项目根")

# ---------- Q3: shade_library 内部怎么锚定数据正本 ----------
print("-" * 64)
print("[9] shade_library 内部写法：")
print("    PROJECT_ROOT = Path(__file__).resolve().parents[2]")
print("    -> 用『自己文件的位置』反推项目根，shades.json 永远找得到，与 cd 无关")

import importlib.util
spec = importlib.util.spec_from_file_location(
    "shade_library_demo", BEAUTY / "lipstick" / "shade_library.py")
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)                     # 按路径直载，绕开包导入链，只测本体
best = sl.search_shade("FF4D6D", top_k=1)[0]
print(f"[10] 实弹 search_shade('FF4D6D') -> #{best['hex']} {best['name']} "
      f"dE={best['dE']}  (模块级加载 shades.json 成功)")

rel = Path("data/shades/shades.json")
print(f"[11] 对照组：相对路径 data/shades/shades.json 存在 = {rel.exists()}   <- 看 cd 脸色")
print(f"     ROOT 锚定的绝对路径存在          = {(ROOT / rel).exists()}   <- 永远 True")
print(SEP)
print("一句话总结：getcwd() 和相对路径随 cd 漂；__file__ 是脚本自己的锚；")
print("            import 只认 sys.path —— 导入链穿过几个目录，就得插几个目录。")
print(SEP)
