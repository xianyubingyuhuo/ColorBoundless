# ColorBoundless · 路线图与计划库（ROADMAP）

> 计划库：记录排期决策与待办功能。新想法先入此库评审，动工时再拆任务。
> 配套文档：系统设计见 `DESIGN.md`，数据流见 `architecture_flow.md`，踩坑见根目录 `避坑注释.md`。
> 最近更新：2026-09-08

## 一、排期决策（带日期，防止遗忘动机）

| # | 日期 | 决策 | 理由 |
|---|---|---|---|
| R-01 | 2026-09-06 | **核心功能优先**，后端/FastAPI 顺延 | 核心功能未完成，后端离当前交付还有距离 |
| R-02 | 2026-09-06 | **vLLM 迁移后置**，不阻塞任何设计 | 换引擎不动架构：OpenAI 兼容接口定了随时可插；被阻塞的只有 function calling 注册这一步 |
| R-03 | 2026-09-07 | **大脑走云端 API**：DeepSeek 实测可用 → 智谱 GLM-5.3-flash 定稿（用户指定），provider 配置可切换 | OpenAI 兼容协议 + 配置中枢（def 7）保证换引擎零改码；API key 实测可用即用 |

## 二、当前主线（P0）

- [x] 核心功能主链路（试妆体验）—— 见下方 def 12，已完成
- [ ] 5 概念总结笔记（用户交付）

## 三、待办池（按优先级）

### ~~P1 · FastAPI 骨架 + `/search`~~ [OK] 超额完成（2026-09-07，commit 4022bd0 / 9beb443 / 2bffd4e）
- def 7 `app/backend/config.py`：provider 可切换配置中枢（secrets.local.json 入 gitignore，fail-fast 校验）
- def 8 `app/backend/llm_client.py`：OpenAI 兼容最薄封装（max_tokens=4096 防推理型模型思维链挤占正文；_error 不穿透）
- def 9 `app/backend/main.py`：三工具 GET 端点 + `/api/chat` + 静态页挂载 + lifespan 预热（kb 模型热加载仅 4s）
- def 10 `app/frontend/index.html`：单文件原生 JS 测试台（三工具卡 + 对话区 + 原始 JSON 折叠 + 工具轨迹展示）
- 一键启动：`.venv/Scripts/python.exe app/backend/main.py` → http://127.0.0.1:8000

### ~~P1 · 工具层 ①②③ 纯函数~~ [OK] 已完成（2026-09-07，commit 77c5bce / eddbe50 / 05e4b34）
- ① `agents/tools/search_shade.py`：normalize_hex + search_shade_tool（importlib 直载算法层，避开 torch/cv2 重依赖链）
- ② `agents/tools/kb_search.py`：embed_query（bge 惰性单例，首问 62s → 后续 6ms）+ kb_search_tool（归一化点积 top-k）
- ③ `agents/tools/palette_search.py`：coarse_candidates（Lab 欧氏粗排 262K→5K）+ palette_search_tool（CIEDE2000 精排，全流程 178ms）
- 统一契约：ok/tool/query/results/error 五件套、错误不穿透、数字由代码算、np 类型转原生
- 备注：② 模型加载慢，FastAPI 启动时需预热一次 embed_query

### ~~P2 · function calling 工具循环~~ [OK] 已完成（2026-09-07，commit 14d4a71）；vLLM 本地迁移仍按 R-03 后置
- def 11 `agents/tools/registry.py`：get_tools_schema（三工具 OpenAI 格式，hue_group enum 动态生成）+ dispatch_tool（未知工具/坏参数兜底五件套 JSON）
- def 11 `app/backend/agent_loop.py`：agent_reply（MAX_ROUNDS=5 防失控、发回消息清洗标准字段、steps 工具轨迹供前端展示）
- `CHAT_SYSTEM` 入 prompt.py（话术资产集中管理；数字原样引用/失败如实转述/闲聊不调工具三条铁律）
- 实测：色号型/知识型/闲聊型三类 + HTTP 端到端全绿；GLM-5.3-flash 会自己带 top_k 参数、引用 dE 数字零心算
- 剩余仅 vLLM 本地部署本身（云端 API 已满足开发与演示）

### ~~P0 · 核心功能主链路（试妆体验）~~ [OK] 已完成（2026-09-08，def 12a-d）
- def 12a `app/backend/tryon_service.py`：run_tryon 五件套（BiSeNet lru_cache 单例，修掉算法层每次调用重载模型的坑；torch 全延迟导入，main.py 启动零负担；base64 出图免静态目录管理；hex 清洗复用工具①门卫 normalize_hex）
- def 12b `main.py` POST /api/tryon：multipart 照片+色号+强度 → run_in_threadpool（冷推理不卡 event loop，chat 并行无损）+ 10MB 限制；新依赖 python-multipart（0.0.32，已入 requirements）
- def 12c `index.html` 试妆卡（门面位）：文件选择 + 色号 + 强度滑条 → 原图/上妆图并排对比 + b64 截断的原始 JSON
- def 12d e2e 全绿：冷调用 654ms（kb lifespan 预热顺手带热 torch/CUDA——延迟导入红利，第二个用 torch 的组件近乎免费）、热调用 72ms、坏 hex/坏图/超限五件套错误、kb_search 回归无损
- 架构决策：试妆走 HTTP 直连，**不进** function calling 注册表——试妆是用户的主动操作（传照片），不是大脑的对话决策
- 测试照片源：`datasets/CelebAMask-HQ/CelebA-HQ-img/`（512×512 人脸 3 万张）
- 已知边界：Lab 迁移只动色度保留原唇明度（保纹理不做塑料唇），深色号视觉偏亮属算法层设计预期

### ~~P0 · def 13 · 全局去 emoji + 前端毛玻璃改版 + CVD 模块自检~~ [OK] 已完成（2026-09-08）
- 全局清理：项目内 24 个文件 emoji 清零（状态符映射 ASCII 标记 [OK]/[NG]/[注意]/[进行中]，装饰符直接删除；vendor 与产物目录不动），规范：今后项目内标题一律不带 emoji
- 前端改版 index.html：全面去圆角（卡片/控件/色块/图片零 border-radius）+ 深色毛玻璃主题（玫红/紫/橙渐变色斑底 + backdrop-filter blur 玻璃卡 + 全方角）
- 体验主流程落地（前端叙事）：页面顶部流程条 01 选色（工具①③）→ 02 上脸试妆 → 03 色盲视角校验（占位，接入中）→ 04 大脑陪聊；五张卡加 STEP 徽标 + 锚点跳转
- def 13a `cvd_test/selftest.py`：色觉测评链自检 22/22 全绿——color_diff 锚点（Lab 标准值、CIEDE2000=Sharma 官方对 2.0425）、cvd_matrix 数学性质（灰轴不动/severity=0 恒等/混淆对 normal ΔE 12.1 vs sim 0.00/protan 红色明度塌陷 L47→36）、石原板正常可见 8.5 vs deutan 隐身 0.2、网格阶梯三维收敛、排列测试 deutan→red-green（轴 170.6°）、triage 快筛三分支 + 档案投票置信封顶
- def 13b 规则库校准（联测真发现）：rules.json cvd_02/cvd_04 的 avoid_pairs 与模拟器行为不符（所选色对明度差大，CVD 下本就不混淆）→ 用 confusion_direction 零空间方向重新生成（tritan：#54857A/#6172B2、#51886A/#646EBA；protan：#BB003A/#3C433A、#C30039/#00473B），source 注明校准来源——"规则库 × 模拟器"闭环是答辩新素材
- 顺手修复：scripts/extract_palette_from_images.py 双 docstring 历史 SyntaxError（git HEAD 即破损）→ 编译通过

### P2 · 定制功能（2026-09-06 新增，完整规格见第四节）

### P2 · AccessibilityValidator（原有规划）
- WCAG 对比度 + CVD 校验，读 `cvd_rules/rules.json`（4 条规则含 protanopia）
- 进展（2026-09-08，def 13）：算法层已就绪并被 selftest 验证（Machado 模拟器 × 规则库闭环 22/22）；剩余：API 端点（模拟预览 /api/cvd/preview + 规则校验 /api/cvd/check）与前端流程 03 步接入

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
   └─ intent = self_view 「面向自己选」 → AccessibilityValidator 校验（CVD 下可区分）
   │
   ▼
search_shade() → 库内最近色号 + dE
   │
   ├─ dE < 2.0 → 推荐库内产品（接 products.json）
   └─ dE ≥ 2.0 → 自动建议定制（用户也可强制提交）
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
