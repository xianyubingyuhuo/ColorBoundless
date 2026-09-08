# -*- coding: utf-8 -*-
"""cvd_test：色觉能力测评模块（project.md 6.9 三测试 → UserColorProfile）

工程化约定与 beauty 一致：接口按模块名分类，不用 __all__。
    color_diff CIE 标准色差（sRGB↔Lab、CIEDE2000）——测评与色号检索共用的地基
    cvd_matrix CVD 模拟矩阵（Machado 2009）+ 混淆方向（零空间）——测试1/校色/双视角的前提
    grid_test 测试2 网格找异色块（阶梯法定量测 ΔL/ΔC/ΔH 分辨阈值）
    ishihara 测试1 伪等色图生成与判定（定性判定色盲类型）
    hue_test 测试3 色相渐变排列（错误轴定位：red-green vs blue-yellow，
                与测试1 构成类型判定双证据链）
    triage 6.15 测评流程状态机：快筛分诊（[绿]/[黄]/[红] + 处方）+ 复诊
                + 多源证据 → UserColorProfile（type 投票/severity/confidence）
"""
from . import color_diff
from . import cvd_matrix
from . import grid_test
from . import ishihara
from . import hue_test
from . import triage
