# base_palette

用于保存从 RGB 色卡等来源提炼出的基础颜色库。

## [注意] 数据源说明（2026-08-13 更新）

**唯一有效数据源 = `full_palette.csv`**（全色域均匀采样，262,144 色，覆盖全部 11 个色相族）

```
原始 "RGB Color Dataset"（R 通道全 ∈[0,4]）已弃用：
- 只有绿/青/蓝色系，几乎没有红/黄/紫（美妆核心色系）
- 已双重验证：文件夹名解析 & 从纯色图片读取，结果一致（偏色）
- 相关文件已删除：rgb_cleaned.csv / rgb_cleaned_summary.json / rgb_from_images.csv
```

> `clean_rgb_dataset.py` 生成偏色数据，**已弃用，请勿运行**。
> 全色域色卡由 `ColorBoundless/scripts/generate_full_palette.py` 生成。

重点字段：
- hex
- rgb
- hsv
- lab
- hue_group
- saturation
- lightness

清洗目标：
- 删除异常值
- 去掉重复色值
- 统一色彩空间
- 生成近似色索引

