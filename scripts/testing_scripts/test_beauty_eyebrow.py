# -*- coding: utf-8 -*-
"""验证 beauty 包工程化接口 + 眉毛上色"""
import sys
from pathlib import Path

# testing_scripts/ 的上上级 = ColorBoundless 根目录，让它可被 import
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from beauty import lipstick, eyebrow

print("=" * 50)
print("[1] 包接口检查（beauty 按模块分类）")
print("lipstick.tryon      ->", lipstick.tryon)
print("lipstick.search_shade ->", lipstick.search_shade)
print("eyebrow.tryon       ->", eyebrow.tryon)
print("=" * 50)

print("[2] 实际眉毛上色（加载 BiSeNet 模型，稍慢）...")
TEST_IMG = r"e:\作业\欧莱雅比赛项目\项目3\ColorBoundless\data\faces\11053.jpg"
result = eyebrow.tryon(TEST_IMG, color="6B4A2B")
print("输出目录:", result)
print("[OK] 眉毛上色完成！")
