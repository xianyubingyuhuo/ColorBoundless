# ColorBoundless · 路线图与计划库（ROADMAP）

> 计划库：记录排期决策与待办功能。新想法先入此库评审，动工时再拆任务。
> 配套文档：系统设计见 `DESIGN.md`，数据流见 `architecture_flow.md`，踩坑见根目录 `避坑注释.md`。
> 最近更新：2026-09-08
>
> **协作背景（2026-09-08 登记，跨会话必读）**：用户为 27 届双非一本应届生。节奏：9 月专注完成本项目（黑客松 9/30 投递），10 月起以本项目为核心投递秋招简历。同时在自学 LeetCode（Python：思路清晰、手写待强化）。
> 分工：产品/架构决策 + 行为验证 = 用户；代码实现 = AI 结对；一切决策落本账本，不靠对话记忆。
> 项目双重终点：① 黑客松可投递、答辩有硬货 ② 成为简历核心项目经历——**用户必须能亲自讲清每个模块**（面试问答稿为正式交付物，见 5.7）。

## 一、排期决策（带日期，防止遗忘动机）

| # | 日期 | 决策 | 理由 |
|---|---|---|---|
| R-01 | 2026-09-06 | **核心功能优先**，后端/FastAPI 顺延 | 核心功能未完成，后端离当前交付还有距离 |
| R-02 | 2026-09-06 | **vLLM 迁移后置**，不阻塞任何设计 | 换引擎不动架构：OpenAI 兼容接口定了随时可插；被阻塞的只有 function calling 注册这一步 |
| R-03 | 2026-09-07 | **大脑走云端 API**：DeepSeek 实测可用 → 智谱 GLM-5.3-flash 定稿（用户指定），provider 配置可切换 | OpenAI 兼容协议 + 配置中枢（def 7）保证换引擎零改码；API key 实测可用即用 |
| R-04 | 2026-09-08 | **多子页架构**：主页只放产品介绍与子页入口，功能模块一律独立子页 | 组件测试期混在主页是权宜，产品化必须分家：模块解耦、演示叙事清晰、主入口不臃肿 |
| R-05 | 2026-09-08 | **AI 不设独立子页**：对话以"伴随 AI"悬浮窗内嵌每个子模块，并能根据用户需求自动调度跳转子页 | 陪聊是全程伴随能力而非孤立功能；AI 调度页面让四步流程串成连贯体验，一个入口承担对话+操作+导航 |

## 二、当前主线（P0）

> 22 天作战表（9/8-9/30；10 月起项目冻结转投递）：**AI 亮点（def 19/20）先行 → 肤色分析/试妆裁剪版/RAG 最小闭环 → 测评组装与投递材料收尾**。排序依据 = 简历叙事价值（面试官听到眼睛一亮的程度），非功能数量。

- [x] 核心功能主链路（试妆体验）—— 见下方 def 12，已完成
- [ ] **第一批 9/8-9/14**：def 19 多子页骨架 + def 20 伴随 AI 悬浮窗（AI 调度 = 最高简历价值，两件同批动工）
- [ ] **第二批 9/15-9/22**：def 16 肤色分析 → def 15 裁剪版（眼影+粉底）→ def 18 RAG 最小闭环（搭配语料由用户 9/15 前提供）
- [ ] **第三批 9/23-9/30**：def 17 测评全链组装进 cvd 子页 + 投递材料（演示视频/截图/文案）+ 全量回归
- [ ] 用户交付：5 概念总结笔记（9 月底定稿）+ 消化面试问答稿
- [ ] 滚动交付：项目深挖面试问答稿（见 5.7，随各 def 产出）

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

### ~~P0 · def 14 · CVD 无障碍进流程（流程 03 真卡）~~ [OK] 已完成（2026-09-08）
- def 14a `app/backend/cvd_service.py`：服务层五件套契约——preview_hex（单色模拟预览：模拟后 hex/ΔE/明度 L 变化）+ check_pair（色对校验：正常 ΔE vs 完全型模拟 ΔE、差值收缩率、verdict 分档、规则库 avoid/safe 命中 + recommended_action）；hex 宽容解析（# 可省/大小写/3 位缩写）、异常不穿透
- def 14b `main.py` 两个 GET 端点：`/api/cvd/preview`、`/api/cvd/check`（挂在静态目录 mount 之前）
- def 14c `index.html`：流程条 03 激活（Machado 模拟 · 规则校验）+ STEP 3 卡（A+B 色对校验 / 清空 B 单色预览双模式，色觉类型下拉 + 严重度滑条）；verdict 阈值 confuse<5 / risky<12 声明为项目启发式（与 selftest safe_pairs 同源），答辩勿引用为行业标准
- 实测四场景：FF4D6D→protan #7B786D（L 59.6→50.4 明度塌陷复现）；红绿对 deutan ΔE 69.85→14.63（收缩 79%，命中 avoid/cvd_01）；B22222/FFFFFF protan 命中 safe/cvd_04；坏 hex 五件套错误
- 剩余（可选）：接入大脑 function calling、灰阶规则 cvd_03 暴露 API

### P2 · 定制功能（2026-09-06 新增，完整规格见第四节）

### ~~P2 · AccessibilityValidator~~ [OK] 已落地（2026-09-08，def 13/14），后继演进见 5.3
- 原规划：WCAG 对比度 + CVD 校验，读 `cvd_rules/rules.json`（4 条规则含 protanopia）
- 现状：CVD 部分已上线——Machado 模拟 + 规则库命中（/api/cvd/preview、/api/cvd/check）+ 流程 03 真卡；算法层 selftest 22/22 背书
- 仍未做：WCAG 对比度校验（并入 5.3 动工时评估）、灰阶规则 cvd_03 暴露 API

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

---

## 五、模块化完善计划（2026-09-08 评审通过，待动工）

> 背景：算法层（Machado 模拟 / CIEDE2000 / 测评套件 / 规则库）已由 cvd_test/selftest 22/22 冻结，进入模块化完善期。
> 架构前提（R-04）：index.html 瘦身为介绍+入口，功能各自成子页，公共样式抽 style.css；
> 本节所有前端工作默认在新子页上进行，主页不再新增功能组件。

### 5.1 def 15 · 试妆全家桶（一整套颜色模拟）
- 现状：仅唇部上线（beauty/lipstick Lab 迁移）；beauty/eyebrow 已有代码雏形
- **范围裁剪（2026-09-08，按简历叙事价值）**：首批只做**眼影 + 粉底**——多部位 `parts` 参数化架构是面试亮点，部位数量不是；画眉后置，口红已上线
- 目标部位：口红（已有）/ **眼影**（l_eye、r_eye + 眼妆区域）/ **画眉**（l_brow、r_brow）/ **粉底**（skin 全脸底色）
- 技术线：BiSeNet parsing 已产出各区域 mask → 扩展 tryon 服务为多部位参数 `parts=[{region, hex, alpha}, ...]`，一次照片、多部位并发上妆、逐部位独立色号与强度
- 前端（tryon 子页）：部位 tab + 每部位独立色号/强度控件，效果图支持逐部位开关对比
- 联动：粉底色号默认取 def 16 肤色分析结果，可微调

### 5.2 def 16 · 上传即分析：肤色自动分析 → 精确色号 → 喂 AI
- 链路：照片 → 人脸 skin 区域采样（避开五官/高光/阴影，Lab 聚类取主色）→ `srgb2lab` 得肤色 Lab → 匹配肤色库（`scripts/process_skin_tone.py` 产物）→ 输出**精确肤色色号** + 冷暖/深浅判定 → ① 自动填入粉底色号 ② 作为用户档案喂 AI（"TA 适合什么颜色"）
- 铁律：肤色 Lab / 色号 / 判定全部由代码算，AI 只引用不心算
- API：`POST /api/skin/analyze`（multipart 照片 → 五件套：skin_hex / skin_lab / undertone / depth / nearest_shade）

### 5.3 def 17 · 色盲纠正：测评全链出档案 → AI 分析
- 测评套件产品化（全部已有，cvd_test/，selftest 22/22 背书）：石原板 + 网格阶梯 + Farnsworth 排列 + triage 状态机
- 流程：用户在 cvd 子页完成完整测评 → triage 输出**色觉档案 JSON**（type / severity / 置信度 / 证据）→ 档案提交 AI 分析：结合 cvd_rules 规则库与 Machado 模拟，输出该用户的个性化用色结论（避开其混淆对、加大明度差、推荐过滤）
- "纠正"口径（答辩一致口径）：不给 TA 凭空补回缺失感知，而是给三件不依赖色觉的凭据（Lab 数值 / 语义色名 / 模拟 hex，见 4.5）+ 档案化的推荐过滤
- AI 侧落点（动工时二选一）：新增工具⑤ get_vision_profile（读档案五件套）或测评档案随 chat 上下文注入

### 5.4 def 18 · RAG 配色改造：AI 自动操作色盘（保留用户权限）
- 数据侧（用户收集）：知识库补充**颜色搭配语料**（搭配组合/场景/适合肤色），量越大越好
- 检索侧：kb_search 命中搭配类语料时**只返回搭配数据本身**（颜色组合、场景、条件），不带任何观点——观点留给 AI
- AI 侧：大脑基于搭配数据思考配色 → function calling 输出**具体色号 JSON**（支持多部位一次给出）
- 前端（tryon 子页）：AI 返回的色号**自动填入**对应部位表单，可一键直接试妆；用户随时可改写/清空/撤销——AI 能自己操作色盘推荐，最终决定权在用户；填充动作由**伴随 AI 悬浮窗**执行（见 5.6，对话与操作同一入口）
- 落点（动工时定）：agent_reply 返回结构扩展 `recommendations=[{region, hex, reason}]` + action 指令（与 def 20 共用同一套 action 通道）

### 5.5 def 19 · 多子页架构改造（先于 5.1-5.4 动工）
- index.html 瘦身：产品介绍 + 四个入口卡（01 选色 / 02 试妆 / 03 色盲校验 / 04 AI 陪聊）
- 子页规划：`palette.html`（工具①③选色）/ `tryon.html`（试妆全家桶 + 肤色分析 + AI 自动填充）/ `cvd.html`（模拟预览 + 色对校验 + 测评全链）——**AI 不设独立子页**，以伴随 AI 悬浮窗内嵌所有子页（R-05，见 5.6）
- 公共：style.css 抽离（毛玻璃主题变量与组件样式，保持零圆角规范）+ 每页统一顶部导航（含返回主页）
- 顺序：先立骨架（页面路由 + 公共样式），再按 tryon 页（5.1→5.2→5.4）与 cvd 页（5.3）分头填充

### 5.6 def 20 · 伴随 AI 悬浮窗（内嵌所有子页 + 自动调度页面）
- 形态：右下角悬浮对话窗（毛玻璃、零圆角、可展开/收起），由 chatbox.js 动态注入 DOM，所有子页共享一套代码；对话历史存 sessionStorage，跨子页跳转后自动恢复上下文
- 能力一：全程陪聊——复用 /api/chat 与现有 agent_loop，四步流程任何一步都可以问
- 能力二：**自动调度页面**——AI 理解用户意图后跳转到对应子页并可带参数（如"这个颜色在色盲眼里什么样" → 跳 cvd.html 并预填色号；"帮我配一套眼妆" → 跳 tryon.html 并自动填充，联动 def 18）
- 落点（倾向方案，动工时确认）：navigate(page, params) 注册为轻量工具，走现有 registry/dispatch 通道——dispatch 识别后不执行数据逻辑，转成返回结构里的 `action={type:"navigate", page, params}` 交给前端执行；与 5.4 的 recommendations 共用同一套 action 通道
- 边界：AI 只发起跳转/填充，表单最终提交权在用户（R-05 原则）；调度是前端行为，不碰后端数据流；AI 调度动作在前端轨迹区可见（可解释）

### 5.7 面试问答稿（正式交付物，2026-09-08 新增）
- 动机：本项目是用户简历的核心项目经历，用户必须能亲自讲清每个模块——既防"AI 代写"面试穿帮，更倒逼真正的理解
- 形式：AI 按面试官视角出 20 问（项目介绍 → 技术深挖如 CIEDE2000/Machado/RAG → 架构取舍如 R-04/R-05 → 失败与重做），每问配答案要点 + 追问链；随各 def 交付滚动更新
- 用户动作：把答案消化成自己的话对着讲；AI 可随时扮演面试官模拟追问（红队训练）
