# ColorBoundless · 路线图与计划库（ROADMAP）

> 计划库：记录排期决策与待办功能。新想法先入此库评审，动工时再拆任务。
> 配套文档：系统设计见 `DESIGN.md`，数据流见 `architecture_flow.md`，踩坑见根目录 `避坑注释.md`。
> 最近更新：2026-09-06

## 一、排期决策（带日期，防止遗忘动机）

| # | 日期 | 决策 | 理由 |
|---|---|---|---|
| R-01 | 2026-09-06 | **核心功能优先**，后端/FastAPI 顺延 | 核心功能未完成，后端离当前交付还有距离 |
| R-02 | 2026-09-06 | **vLLM 迁移后置**，不阻塞任何设计 | 换引擎不动架构：OpenAI 兼容接口定了随时可插；被阻塞的只有 function calling 注册这一步 |

## 二、当前主线（P0）

- [ ] 核心功能主链路（试妆体验）—— 待拆解
- [ ] 5 概念总结笔记（用户交付）

## 三、待办池（按优先级）

### P1 · FastAPI 骨架 + `/search`（原定 9/6，因 R-01 顺延）
- `app/backend` 起骨架：健康检查 + `POST /search` 直连 `shade_library.search_shade`
- 不依赖 vLLM，随时可插队

### ~~P1 · 工具层 ①②③ 纯函数~~ ✅ 已完成（2026-09-07，commit 77c5bce / eddbe50 / 05e4b34）
- ① `agents/tools/search_shade.py`：normalize_hex + search_shade_tool（importlib 直载算法层，避开 torch/cv2 重依赖链）
- ② `agents/tools/kb_search.py`：embed_query（bge 惰性单例，首问 62s → 后续 6ms）+ kb_search_tool（归一化点积 top-k）
- ③ `agents/tools/palette_search.py`：coarse_candidates（Lab 欧氏粗排 262K→5K）+ palette_search_tool（CIEDE2000 精排，全流程 178ms）
- 统一契约：ok/tool/query/results/error 五件套、错误不穿透、数字由代码算、np 类型转原生
- 备注：② 模型加载慢，FastAPI 启动时需预热一次 embed_query

### P2 · vLLM 迁移 + function calling（R-02 后置）
- 工具①②③④ 注册 function calling，挂 OpenAI 兼容 `/chat/completions`

### P2 · 定制功能（2026-09-06 新增，完整规格见第四节）

### P2 · AccessibilityValidator（原有规划）
- WCAG 对比度 + CVD 校验，读 `cvd_rules/rules.json`（4 条规则含 protanopia）

---

## 四、定制功能设计规格（方向已评审，待动工）

> **动机**：CVD 模拟有天花板——无法让色盲用户"看见"TA 一辈子没见过的颜色，模拟合成救不了感知缺失。
> 所以体验闭环必须落到**现实手段**：选号阶段用模拟 + 校验兜底；库内没货就**提交定制**。
> 定制功能 = 人文关怀从展示层走到交易层。

### 4.1 定位与边界
- 定制**价格由商家决定**，本系统只做需求流转（status 流转，price 字段留空）——不碰定价，边界清晰
- 色盲用户与普通用户**共用同一个定制出口**：普通用户对推荐不满意也可提交

### 4.2 流程：两条意图，一个出口

```text
用户选号（hex / 场景 / 描述）
   │
   ├─ intent = normal_view「以正常人色感选」→ CVD 模拟预览（看别人眼中的效果）
   └─ intent = self_view    「面向自己选」  → AccessibilityValidator 校验（CVD 下可区分）
   │
   ▼
search_shade() → 库内最近色号 + dE
   │
   ├─ dE < 2.0  → 推荐库内产品（接 products.json）
   └─ dE ≥ 2.0  → 自动建议定制（用户也可强制提交）
                     │
                     ▼
              POST /custom-requests → 定制单落盘 → 商家接单（status 流转）
```

### 4.3 双意图（本功能的人文核心）
- **normal_view**：色盲用户想以正常人色感呈现自己——产品只服务这一种的商业现状，我们不接受
- **self_view**：色盲用户按自己的感知与偏好选——同样是正当需求
- 普通商业产品从不区分这两种意图，本系统显式建模

### 4.4 定制单 schema

```json
{
  "request_id": "CR-20260906-001",
  "created_at": "2026-09-06T20:00:00",
  "vision_type": "deuteranopia",
  "intent": "normal_view",
  "target_hex": "#B34A5A",
  "target_lab": [46.2, 38.5, 8.1],
  "nearest_shade": {"name": "豆沙红", "hex": "#A63A2B", "dE": 6.8},
  "reason": "dE_above_threshold",
  "cvd_report": {
    "simulated_hex": "#8A6B5E",
    "distinct_ok": true
  },
  "status": "submitted",
  "price": null
}
```

- `target_lab` 服务端用 `hex2lab` 计算，不信前端（铁律：算出来的不手写）
- `reason` 自动判定：`dE_above_threshold` / `user_forced` / `no_match_in_library`
- `status`：`submitted → accepted → quoted → produced`（商家侧字段只留枚举）

### 4.5 关键设计：三样"不需要眼睛的确认物"
色盲用户无法用眼睛验收颜色，给他三样不依赖色觉的凭据：
1. **Lab 数值**——物理量，永远客观
2. **语义色名**——语言可信（shades.json 的 name/desc 已有此基础）
3. **CVD 模拟 hex（cvd_report）**——不是让 TA 看见，是给**生产端**的客观标准：商家照此生产、照此验收 dE

### 4.6 自动判定
- `dE < 2.0`（近似不可辨差）→ 推荐库内产品
- `dE ≥ 2.0` → 建议定制；用户可无视建议强制提交（reason 记 `user_forced`）

### 4.7 落点（四层，全增量，零改动现有模块）
| 层 | 位置 | 内容 |
|---|---|---|
| 数据 | `data/custom_requests/` | 一单一个 json |
| 服务 | `beauty/lipstick/custom.py` | `create_custom_request()`，复用 `hex2lab`/`ciede2000`，约 60 行 |
| 工具 | `agents/tools/` | 工具④ `submit_custom`（函数本体先行，vLLM 来了直接注册） |
| API | `app/backend` | `POST /custom-requests`、`GET /custom-requests/{id}` |

### 4.8 动工前置条件
- [ ] 核心功能主链路完成（R-01）
- [ ] FastAPI 骨架落地（/search 先行）
- [ ] `data/products/products.json` 最小样例 5-8 条（brand / name / shade_ref→hex / price / url）——"匹配产品库"环节目前不存在实体，无它则"推荐 vs 定制"的分界线悬空
