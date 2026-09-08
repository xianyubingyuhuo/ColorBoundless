# cosmetics_kb — 美妆专业知识语料库（RAG 用）

本目录是 **RAG 语义检索的文本语料源**（JSONL，一条一个 JSON 对象）。
管线分工与 `style_recommendations` 完全一致：

```
本目录 *.jsonl ──scripts/build_cosmetics_kb.py──▶ models/vector_store/cosmetics_kb_index.npz（文本索引）
                                    │
                                    └──scripts/embed_cosmetics_kb.py──▶ cosmetics_kb_embeddings.npz（bge 向量）
```

检索命中后从 index.npz 取**原文**交给 LLM，所以本目录文件必须随仓库保留。

## 语料 schema（每行一个 JSON 对象）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | str | [OK] | 全库唯一，建议来源前缀：`seed_`（自写）/ `wiki_` / `brand_` / `cvd_` |
| `category` | str | [OK] | `color_theory` / `technique` / `style` / `cvd` / `product` / `vocab` |
| `title` | str | [OK] | 条目标题（参与检索文本） |
| `content` | str | [OK] | 正文，**检索友好改写**：口语化提问开头 + 同义词嵌入，200~600 字 |
| `tags` | list[str] | [OK] | 口语词/同义词/俗称（提升召回率的关键，如"黄皮""浆果色"） |
| `source` | str | [OK] | 来源出处（版权 + 可信度，答辩可引用） |
| `occasion` | list[str] | - | 统一词汇表：`daily` / `work` / `date` / `party` / `night` / `formal` / `photo` / `all` |
| `hue_family` | str | - | 所属色系（如 `cool_violet`、`warm_red`） |

## 写作原则（决定 RAG 质量）

1. **原子条目**：一条只回答一个问题，宁多勿长；
2. **面向检索改写**：正文第一句用用户会问的口语（"黄皮涂什么色号不显黑？"），
   并在文中自然嵌入同义词——这不是抄网页，是"检索友好转写"；
3. **来源必填**：事实性数据（色号数值/成分/对比度公式）可自由使用，
   品牌营销文案与教材原文**只转写不复制**；
4. **控量重质**：200~500 条精选条目 > 2 万条爬虫杂讯（与 style_recommendations 同一原则）。

## 来源分层（版权风险从低到高）

- **A 自有资产**：`docs/DESIGN.md` 六/七/八节（配色类型、科学美学规则）→ `seed_techniques.jsonl`
- **B 权威机构**（低风险，事实数据）：WCAG 2.x 对比度公式（W3C）、Colour Blind Awareness
  （CVD 类型/患病率）、Colblindor、药监局《化妆品分类规则》、Wikipedia 色彩条目（CC BY-SA 需署名）
- **C 品牌色号库**（只取事实：色号/Lab/质地/色调）：MAC/NARS/CT/Fenty/花西子/Judydoll 官网、Temptalia、
  Kaggle `Cosmetic Foundation Shades`（已在 download_materials）
- **D 社区/教材**（高风险，人工转写）：B站文字稿、小红书/知乎（价值在口语问法 → tags）、
  美妆教材（转写不复制）

## 场合词汇约定（全项目统一：shades.json / base_palette / 本语料，build 脚本强制校验）

`occasion` 只允许 8 词：`daily` / `work` / `date` / `party` / `night` / `formal` / `photo` / `all`。

旧词 → 新词映射：evening→`night`，social/event→`party`，
portrait/shooting/editorial/stage/fashion→`photo`，soft-glam/travel→`daily`。
中文对照：日常→`daily`，通勤/上班→`work`，约会→`date`，派对→`party`，
晚宴/夜场→`night`，正式/宴会/婚礼→`formal`，拍照/出片/舞台→`photo`。

风格词（气场/温柔/复古等）**不进 occasion**——放 `emotion`（或 tags），场合与风格两维正交。
