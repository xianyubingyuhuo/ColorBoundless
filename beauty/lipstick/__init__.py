# -*- coding: utf-8 -*-
"""lipstick 包：口红模块

统一接口：
    tryon(img_path, color=...)   虚拟试妆
    search_shade(query_hex, top_k)  色号检索（CIEDE2000）
"""
from .tryon import tryon
from .shade_library import search_shade

