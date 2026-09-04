# cvd_rules

色盲 / 可访问性规则库，用于保证调色方案在不同视觉条件下仍可辨识。
消费方：算法层 `AccessibilityValidator`（规划中，见 data/README.md 5.3.6）与 Agent 的事实引用。

## 当前内容（与 rules.json 实物一致）

| rule_id | cvd_type | 规则 |
|---|---|---|
| cvd_01 | deuteranopia | 红绿混淆：avoid/safe 色对，用明度差与中性色过渡降低误判 |
| cvd_02 | tritanopia | 蓝黄混淆：低饱和场景需保留明度层次，蓝黄不直接并置 |
| cvd_03 | global | 灰阶可读性：亮度差 ≥ 0.18（**项目自定义启发式阈值**） |
| cvd_04 | protanopia | 红色明度塌陷：深红↔深绿/棕褐易混淆，需明度差 + 非颜色冗余编码 |

每条规则的 `source` 字段标注事实来源；CVD 颜色模拟实现在 `cvd_test/cvd_matrix.py`。

## 规划中（落地前勿在答辩中引用为已实现）

- `contrast_ratio_threshold`：WCAG 对比度校验 → 归入 AccessibilityValidator
- `low_saturation_safe_set` / `color_confusion_pair_list`：待补数据
