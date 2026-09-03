# -*- coding: utf-8 -*-
"""beauty 包：美妆各品类模块

组织方式：按品类子包分类，每个子包通过自己的 __init__.py 暴露统一接口。
（不用 __all__ 扁平清单，而是用「模块名」作为分类 —— 谁是什么一目了然）

用法：
    from beauty import lipstick, eyebrow
    lipstick.tryon("photo.jpg", color="FF4D6D")   # 口红
    eyebrow.tryon("photo.jpg", color="6B4A2B")    # 眉毛
    lipstick.search_shade("FF4D6D")               # 色号检索
"""
from . import common
from . import lipstick
from . import eyebrow

