# data 模块

数据层负责不同来源的色彩与图像样本管理，遵循“原始数据保留 + 规范化落库 + 知识规则生成”的分层原则。

## 1. 分层结构

- raw_sources: 原始下载数据，保持来源真实性，不做业务层加工
- knowledge_base: 真正用于推荐与检索的事实库
- processed: 清洗后的结构化数据
- color_test_questions: 色盲 / 可访问性测试题库，用于规则验证和安全评估

### 1.1 数据生产（scripts）与数据消费（程序）解耦

- **数据从哪来**：`../scripts/` 是"一次性数据工厂"——运行 `process_*.py` / `embed_*.py` 产出 `models/vector_store/*.npz` 检索索引
- **程序依赖边界**：运行时只依赖 `models/vector_store/` 的产物（npz），**不依赖 scripts 代码本身**（业务代码里不会有 `from scripts.xxx import`）
- **scripts 可分离**：它留在项目内仅作为"可复现（数据更新重跑）+ 答辩凭证（数据从哪来）"，架构上完全可移到项目外，不影响程序运行
- **更新数据的标准流程**：改数据源 → 重跑对应 `process_*.py` → 跑 `verify_indexes.py` 验证四索引 → 程序自动读到新数据

## 2. 数据源映射

### 2.1 基础色板

- 主要来源：RGB 色卡数据
- 目标字段：hex, rgb, hsv, lab, hue_group, lightness, saturation
- 清洗规则：
  - 删除空值、非十六进制数据
  - 去重，保留唯一色值
  - 统一成 6 位 HEX 或 RGB 三元组
  - 计算 Lab / HSL / HSV 特征
  - 生成近似色索引和色相族标签

### 2.2 肤色与底妆数据

- 主要来源：肤色数据集、化妆品色号数据
- 目标字段：skin_tone_label, undertone, fitzpatrick, rgb, hex, product_category
- 清洗规则：
  - 统一命名：cool / warm / neutral
  - 规范颜色表示为 HEX + RGB + Lab
  - 对缺失的 undertone 进行规则补全
  - 将不同品牌的色号映射到统一的基础色板
  - 生成“肤色-底妆色号”对应表

### 2.3 视觉妆容数据

- 主要来源：妆容图、面部检测数据、 makeup 任务数据
- 目标字段：image_path, face_bbox, makeup_label, style_tag, skin_tone
- 清洗规则：
  - 过滤低分辨率、模糊、遮挡严重图片
  - 统一人脸框与分割要求
  - 标准化妆容标签（有妆 / 无妆 / 口红 / 眼影 / 腮红 / 眉妆）
  - 仅保留高质量样本用于训练与视觉参考

### 2.4 风格与推荐数据

- 主要来源：推荐 CSV、时尚标签数据
- 目标字段：style, occasion, color_pair, hex_list, tags
- 清洗规则：
  - 删除 NaN、重复记录
  - 统一标签语言（例如 soft / bold / vintage / editorial）
  - 将颜色列表转成标准的 palette 结构
  - 单条记录必须对应一个明确的风格语义

### 2.5 CVD 与可访问性数据

- 主要来源：色盲模拟与对比度测试数据
- 目标字段：pair_a, pair_b, simulation_type, contrast_ratio, safe_score
- 清洗规则：
  - 计算 CVD 模拟后对比度
  - 标记“可辨识 / 可读 / 不适合”评级
  - 包含阈值规则，方便后续安全过滤

## 3. 训练任务拆分

### 3.1 基础色板训练任务

- 任务：颜色检索、相近色推荐、色相聚类
- 模型建议：
  - 颜色 embedding / FAISS / vector search
  - KNN 颜色匹配
  - 聚类模型（KMeans / HDBSCAN）

### 3.2 肤色分类任务

- 任务：undertone / skin tone 分类
- 模型建议：
  - 传统机器学习：XGBoost / LightGBM
  - 或轻量图像分类网络（MobileNet / ResNet18）
- 推荐输出：cool / warm / neutral + 深浅档位

### 3.3 时尚推荐任务

- 任务：风格与搭配排序
- 模型建议：
  - pairwise ranking model
  - lightweight recommender
  - LLM + vector retrieval 结合
- 推荐格式：
  - 0.7 / 0.8 / 0.9 安全评分
  - 适合场景标签
  - 配色结构说明

### 3.4 视觉妆容任务

- 任务：妆容检测 / 分割 / 风格识别
- 模型建议：
  - face parsing: BiSeNet / DeepLab
  - makeup classification: MobileNet / ViT
- 训练目标：
  - 识别妆容区域
  - 判断是否有妆
  - 关联肤色和颜色风格

### 3.5 CVD 安全过滤

- 任务：对推荐结果做“可辨识性”过滤
- 逻辑：
  - 对候选配色做 CVD 模拟
  - 计算 contrast ratio
  - 除去低对比、低识别配色
  - 给出安全评分

## 4. 落库建议

- 原始数据保留在外部下载区，不混入项目主目录
- 项目内只保留处理后的规范化数据和事实知识库
- 数据处理脚本可以统一放入 data/processed 或后续 scripts/
- 每个数据源都需要最终产出一个统一 schema，方便后续训练和 RAG 检索

注意：测试题库属于“规则与评估数据”，而不是直接放在主程序业务逻辑里。真正的核心逻辑应当在主程序 / agent / cv / rag 模块中实现。

## 5. 数据集处理状态与接入方式总览（2026-08-13 更新）

### 5.0 接入总原则（工业级架构）

```
结构化数据（颜色/产品库） → 算法底层直接检索（快、准、无幻觉，不进 LLM）
知识性数据（风格/规则）   → Agent 的 RAG 知识库（精选、去噪，防幻觉）
规则数据（配色/CVD）      → 代码内直接调用（校验器/引擎，确定性逻辑）
用户动态信息（偏好/历史） → 记忆系统 memOS（不进 RAG）
```

> 依据：RAG 是知识库，塞太多容易出幻觉。能结构化算的绝不让 LLM 猜。

### 5.1 状态图例

- ✅ 已处理（已生成可检索索引 → `models/vector_store/`）
- 📝 已整理（人工整理好的 json / 规则，可直接使用）
- ⬜ 未处理（只有 README 规划或目录为空）

### 5.2 数据集总览表

| 数据集 | 位置 | 状态 | 接入层 | 接入方式 |
|---|---|---|---|---|
| **base_palette** | `processed/base_palette/full_palette.csv` + `models/vector_store/base_palette_index.npz` | ✅ | 算法底层（颜色匹配引擎） | KMeans 簇 + Lab 色差（CIEDE2000） |
| **skin_tone** | `processed/skin_tone/skin_tone_cleaned.csv` + `skin_tone_index.npz` | ✅ | 算法底层（底妆筛选） | undertone×lightness 查询表 O(1) + Lab 精排 |
| **style_recommendations** | `processed/style_recommendations/fashion_style_cleaned.csv` + `style_recommendations_index.npz` + `style_recommendations_embeddings.npz` | ✅ | Agent（RAG 知识库） | 特征组合过滤 + rule_texts 语义检索（512维 bge 向量，已验证） |
| **shades.json** | `shades/shades.json` | 📝 | Agent（产品知识） | 美妆色号精选库：查表 / 转 RAG 文档 |
| **color_rules** | `knowledge_base/color_rules/rules.json` | 📝 | 算法底层 + Agent | 代码内调用（配色引擎）+ LLM 解释依据 |
| **cvd_rules** | `knowledge_base/cvd_rules/rules.json` | 📝 | 算法底层（安全校验器） | 输出前 CVD 校验（AccessibilityValidator） |
| **base_palette/*.json** | `knowledge_base/base_palette/`（red/purple） | 📝 | 算法底层 | 特定色系基础色，供色系检索 |
| **style_palette/*.json** | `knowledge_base/style_palette/`（cold_violet 等） | 📝 | Agent（RAG） | 风格调色板，语义检索 |
| **faces/** | `faces/11053.jpg` + mask | 📝 | CV 测试 | 人脸检测/分割/试妆的测试输入 |
| **color_test_questions** | `color_test_questions/` | ⬜ | 算法底层（评估） | 色盲测试题库，待创建 |
| **color_cards** | `color_cards/` | ⬜ | — | 空，待规划 |
| **palettes** | `palettes/` | ⬜ | — | 空，待规划 |

### 5.3 各数据集详细接入方式

#### 5.3.1 base_palette（颜色库）✅

- **接入层**：算法底层 → `beauty/` 或 `cv/` 的颜色匹配引擎
- **接入方式**：纯结构化检索，**不进 LLM / RAG**
  ```python
  # 方式1：按色相族过滤（如"红色系"）
  red_idx = np.where(idx["hue_group_labels"] == HUE_RED)[0]

  # 方式2：Lab 色差找最近色（推荐用 CIEDE2000）
  # 先 KMeans 找最近簇 → 簇内精排，避免全量扫描
  nearest = find_nearest_by_lab(idx, target_lab, top_k=5)
  ```
- **谁在用**：推荐系统的"颜色匹配模块"（把理论颜色 → 具体色号）

#### 5.3.2 skin_tone（产品库）✅

- **接入层**：算法底层 → `beauty/foundation` 底妆模块
- **接入方式**：结构化过滤 + Lab 精排
  ```python
  # 方式1：结构化过滤（O(1) 字典查询）
  # key = "undertone_id_lightness_id"，如 warm+light = "1_2"
  warm_light = idx["lookup"]["1_2"]

  # 方式2：与用户肤色算色差，取最接近的产品
  best = min(candidates, key=lambda p: ciede2000(p.lab, user_skin_lab))
  ```
- **谁在用**：底妆推荐（用户肤色 → 合适色号）

#### 5.3.3 style_recommendations（风格规则库）✅

- **接入层**：Agent → 推荐 Agent 的 RAG context
- **接入方式**：双通道（结构化 + 语义）
  ```python
  # 通道1：特征组合过滤（用户 发色/眼色/肤色/色调）
  rules = idx["lookup"]["0_1_2_0"]   # 精确匹配

  # 通道2：语义检索（rule_texts 转 embedding，走向量库）
  # 匹配的规则作为 context 喂给 LLM 生成推荐
  context = format_rules(matched_rules)
  ```
- **谁在用**：推荐 Agent（LangChain RAG 管道的知识来源）

#### 5.3.4 shades.json（美妆色号精选库）📝

- **接入层**：Agent → 妆容推荐 Agent
- **接入方式**：精选口红/妆容色号，可直接查表；也可转成 RAG 文档
- **用途**：生成"具体口红推荐"（复古红棕、元气正红、玫红…）
- **后续**：可选将其 embedding 化，纳入向量库做语义搜索

#### 5.3.5 color_rules（配色规则）📝

- **接入层**：算法底层（配色引擎）+ Agent（解释依据）
- **接入方式**：每条规则是确定性逻辑，代码内直接调用
  ```python
  # 例：split_complementary / analogous_soft / monochrome_balance
  palette = apply_color_rule("analogous_soft", base_color)
  ```
- **谁在用**：beauty 层配色引擎；同时规则文本可给 LLM 作"为什么这样配"的依据

#### 5.3.6 cvd_rules（色盲安全规则）📝

- **接入层**：算法底层（安全校验器）→ `AccessibilityValidator`
- **接入方式**：推荐输出前强制校验
  ```python
  if not validator.check_cvd_safe(rec_pair, rule="red_green_confusion"):
      rec_pair = validator.apply_safe_fallback(rec_pair)
  ```
- **谁在用**：推荐管线最后的"安全过滤"环节（防色盲用户误判）

#### 5.3.7 faces/（测试人脸）📝

- **接入层**：CV 测试
- **接入方式**：MediaPipe / OpenCV 人脸检测、分割、虚拟试妆的**测试输入**
- **用途**：验证 `cv/` 层算法正确性

#### 5.3.8 color_test_questions（色盲测试题库）⬜ 未处理

- **状态**：仅 README 规划，无数据
- **计划**：生成色盲 / 可访问性测试题库，用于规则验证和安全评估
- **接入方式**：算法底层（评估）——对推荐结果做可辨识性打分

### 5.4 未处理 / 待规划清单

| 目录 | 现状 | 建议 |
|---|---|---|
| `color_test_questions/` | 空 | 下一阶段生成 CVD 测试题库 |
| `color_cards/` | 空 | 如需特定品牌色卡再填充 |
| `palettes/` | 空 | 可存放组合调色板（与 style_palette 复用）|
| `faces/` | 1 组测试图 | 后续补充多肤色/多场景测试图 |

