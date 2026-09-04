# base_palette

基础色卡库：按色系存放"单色号的底层属性"，供色系检索与 Agent 工具读取。

## 文件

- `red_base.json` / `purple_base.json`（现有）
- 预留：brown_base / neutral_base / soft_pink_base

## 字段 schema

| 字段 | 说明 |
|---|---|
| `palette_id` | `base_<色系>_<序号>`，全库唯一 |
| `hex` / `rgb` / `lab` | 颜色本体（Lab 为 sRGB→D65 标准转换） |
| `category` | `lip` / `eyebrow` / `eyeshadow` |
| `hue_family` | 色相族（与 process_base_palette.py 的 11 族命名一致） |
| `undertone` / `lightness` / `saturation` | warm-cool / bright-medium-dark(dim) / high-medium |
| `emotion` | 风格词闭集（见下） |
| `occasion` | 场合闭集 8 词（见下） |
| `cvd_safe` | ⚠️ 启发式人工评估分 [0,1]，**未经公式验证**（见下方声明） |
| `notes` | 一句话适用说明 |

## occasion 场合闭集（全项目统一，cosmetics_kb 管线强制校验）

`daily` / `work` / `date` / `party` / `night` / `formal` / `photo` / `all`

旧词映射：evening→night，social/event→party，portrait/shooting/editorial/stage/fashion→photo，soft-glam/travel→daily。
中文对照：日常→daily，通勤/上班→work，约会→date，派对→party，晚宴/夜场→night，正式/宴会/婚礼→formal，拍照/出片/舞台→photo。

## emotion 风格词闭集

`vibrant` `confident` `romantic` `soft` `fresh` `youthful` `mature` `luxury` `edgy` `vintage` `elegant` `playful`

## cvd_safe 的诚实声明

当前数值为**人工启发式评估**（0 = 色盲视角极易混淆，1 = 高度可辨），无文献支撑；
答辩中应作为"设计参考值"而非"实验结论"引用。
TODO：接入 `cvd_test/cvd_matrix.py` 的 CVD 模拟矩阵，对"色号 vs 典型肤色 #F0D0B8"计算 WCAG 对比度并归一化，使数值可复现。
