# processed

该目录保存清洗后的规范化数据，属于正式项目数据层。

内容包括：
- base_palette: HEX / RGB / Lab / 色相族处理后的颜色库
- skin_tone: 肤色分类和 undertone 数据
- style_recommendations: 风格标签和搭配规则

所有数据在进入训练前，必须满足统一 schema：
- hex / rgb
- 统一标签名
- 统一字段命名
- 统一质量过滤标准
