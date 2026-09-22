# ColorBoundless · 路线图与计划库（ROADMAP）

> 计划库：记录排期决策与待办功能。新想法先入此库评审，动工时再拆任务。
> 配套文档：系统设计见 `DESIGN.md`，数据流见 `architecture_flow.md`，踩坑见根目录 `避坑注释.md`。
> 最近更新：2026-09-18
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
| R-09 | 2026-09-16 | **早鸟 10/7**：功能冻结倒计时——仅收尾产品库激活+def18 回填最小版（1-2 天）；材料阶段用户自任视频剪辑(PR)与 PPT 排版(Office)，AI 交付分镜脚本(docs/演示视频分镜.md)、PPT 文案(docs/PPT大纲.md)、README 打磨；def 16/穿搭扩展写 PPT"规划中" | 用户具备 PR/PPT 技能；剩余风险在材料质量与时间而非功能 |
| R-10 | 2026-09-18 | **新增学习线：大模型安全——欧莱雅项目全部收尾后（10 月初）才启动，9 月内零占用**：以 OWASP LLM Top 10 为纲体系化学习 + def 23 红队评测项目（给本项目自己做安全评测）；理由：① def 22m 已有防御雏形（注入入口检测/泄露出口扫描/navigate 白名单）但从未评测过覆盖率与漏报率 ② 岗位差异化：会用 AI 的人多，给 AI 系统做过系统化安全评测的人极少 ③ 项目制学习产出直接进简历与 5.7 面试问答稿 | 安全与评测是 AI 的成本项——泡沫叙事下的正面回答；材料阶段（9/17-10/7）精力 100% 给欧莱雅，本决策仅为立项备忘 |

## 二、当前主线（P0）

> 22 天作战表（9/8-9/30；10 月起项目冻结转投递）：**AI 亮点（def 19/20）先行 → 肤色分析/试妆裁剪版/RAG 最小闭环 → 测评组装与投递材料收尾**。排序依据 = 简历叙事价值（面试官听到眼睛一亮的程度），非功能数量。

- [x] 核心功能主链路（试妆体验）—— 见下方 def 12，已完成
- [x] **第一批 9/8-9/14**：def 19 多子页骨架 + def 20 伴随 AI 悬浮窗 v1 —— **2026-09-11 完成**：`style.css` 抽取共享（毛玻璃锚点保留）；主页 R-04 化（纯入口+算法底座卡）；`palette/tryon/cvd.html` 三子页上线（原功能零迁移损失，ID 不变；def 15/16/17 预留注释位）；`chatbox.js` 自注入悬浮窗（零配置引入即生效，五件套轨迹可见，**def 18 fill / def 20 navigate 的 action 通道已预留**）；后端零改动（StaticFiles 自动覆盖），六资源 200 + CVD 冒烟与 def 14 数据一致
- **def 17 收口反馈 bug 修复（2026-09-13，两起）**：① **色彩校验"分析"无反应**——根因：cvd.html 布局重构（左选项卡版）时 **cvd()/cvdVerdict() 函数在重建中遗漏**，按钮 onclick 调用未定义函数（Console 有 cvd is not defined）；已补回完整 def 14 逻辑（模拟预览/色对校验/规则命中渲染）。**流程教训**：页面重建必须对照旧文件函数清单逐一核对——已记入自检清单。② **便签 hover"透明方框"观感**（用户二次反馈）——方框式 hover（毛玻璃底/品牌底）观感始终像"透明框"，**改为品牌色底线滑入**（2px 底线 scaleX 动画，无框）；全站五页 style.css 版本 bump def17c
- [x] **def 19b 主页改版 + def 20 v2**（2026-09-11，用户口头需求）：① 主页右上导航标签（`|` 分隔、hover 0.25s 淡入毛玻璃边框）替换原卡片底框；② 幻灯片区（5s 轮播+圆点，`slides/01~03.jpg` 存在即自动接管占位帧）；③ 色盲科普框（真实原理两段+待扩充标注）；④ 支持区（GitHub/反馈占位）；⑤ 主标题放大 38px 渐变字；⑥ **R-04 修正（用户指示）**：伴随 AI 于全站页面常驻（含主页）——主页仍无功能组件，AI 属全局陪伴非页面功能；⑦ **def 20 v2**：对话记录 sessionStorage 跨页重放 + 展开状态还原 + AI 球自由拖动（>5px 判拖/≤5px 判点，位置 localStorage 持久）+ 面板实时锚定防溢出 + resize 自愈
- [x] **第二批 9/15-9/22（用户旅程顺序 2026-09-11 修订：测评 → 校色 → 试妆）**：**def 17 全链完成（后端 API + 档案 + 试妆校色联动 + 工具⑤ + cvd 页测评 UI + 档案卡 + AI 总结钩子 + 校色选择器 + R-06 全站换肤，全部实测）** → def 15 聚合式试妆 → def 16 肤色分析 → def 18 RAG 最小闭环（搭配语料由用户提供）
- [x] **骨架增补（2026-09-11，用户需求）**：`products.html` 产品库子页上线（全站第五便签 + on 渐变高亮同款）——定位：def 17 测评完成后 AI 携推荐结果跳转的落点、tool④（submit_custom / products.json）数据的 UI 归宿、def 18 RAG 色号→在售产品匹配的展示端；当前为"建设中"占位卡，API 就绪后激活渲染脚本
- [x] **def 20 v2.1 AI 球视觉收敛（2026-09-11）**：圆形 56px + 外环背景同源渐变（粉→品红→紫）+ 内圆改背景蓝黑（去淡蓝亮色）+ "AI"白字 + hover 0.45s 缓动放大 1.09 与品牌粉微光 + 按住拖动回归原尺寸
- [ ] **第三批 9/23-9/30**：def 17 收口——cvd 页测评 UI（三题型渲染+进度条）+ 档案展示卡 + AI 总结钩子 + 校色选择器（R-06 双模式开关接 /calibrate + 全站换肤）→ 投递材料（演示视频/截图/文案）→ 全量回归
- [x] **def 15 聚合试妆收口（2026-09-16，v13）**：唇/粉底/眼影/**眉**四部位聚合（眼影=眼皮皮肤带掩码·眼球零接触；粉底=磨皮+Lab 全通道迁移；brow=(2,3) 打通）；商品匹配 ΔE≤5 有货/定制；全站前端拆分三件套（405 HTML/194 CSS/1380 JS）
- [ ] **材料阶段（2026-09-17 → 10/7 早鸟，R-09）**：① 产品库激活 + def18 回填最小版（1-2 天）→ 功能冻结 ② 分镜脚本已交付 docs/演示视频分镜.md → OBS 录制 → PR 剪辑 ③ PPT 文案已交付 docs/PPT大纲.md → Office 排版 ④ README 评委版 + 全量回归 ⑤ 10/6-10/7 提交（含缓冲）
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
- 前端（tryon 子页）**交互改版（2026-09-11 用户定稿）：去 STEP 化，单卡聚合**——上传照片一次 → 部位 chips（唇/眼影/粉底…）逐个点选并为每部位挑色号/强度"添加" → `parts=[{region,hex,alpha},...]` 一次提交上妆；效果图支持逐部位开关对比。不再分步卡片
- 联动：粉底色号默认取 def 16 肤色分析结果，可微调

### 5.2 def 16 · 上传即分析：肤色自动分析 → 精确色号 → 喂 AI
- 链路：照片 → 人脸 skin 区域采样（避开五官/高光/阴影，Lab 聚类取主色）→ `srgb2lab` 得肤色 Lab → 匹配肤色库（`scripts/process_skin_tone.py` 产物）→ 输出**精确肤色色号** + 冷暖/深浅判定 → ① 自动填入粉底色号 ② 作为用户档案喂 AI（"TA 适合什么颜色"）
- 铁律：肤色 Lab / 色号 / 判定全部由代码算，AI 只引用不心算
- API：`POST /api/skin/analyze`（multipart 照片 → 五件套：skin_hex / skin_lab / undertone / depth / nearest_shade）

### 5.3 def 17 · 色盲纠正：测评全链出档案 → AI 分析
- 测评套件产品化（全部已有，cvd_test/，selftest 22/22 背书）：石原板 + 网格阶梯 + Farnsworth 排列 + triage 状态机
- 流程：用户在 cvd 子页完成完整测评 → triage 输出**色觉档案 JSON**（type / severity / 置信度 / 证据）→ 档案提交 AI 分析：结合 cvd_rules 规则库与 Machado 模拟，输出该用户的个性化用色结论（避开其混淆对、加大明度差、推荐过滤）
- "纠正"口径（答辩一致口径）：不给 TA 凭空补回缺失感知，而是给三件不依赖色觉的凭据（Lab 数值 / 语义色名 / 模拟 hex，见 4.5）+ 档案化的推荐过滤
- AI 侧落点（2026-09-11 已实现）：**工具⑤ get_vision_profile_tool 已注册**（读档案五件套，AI 总结话术的数据源）
- **def 17a 测评 API（2026-09-11 完成，实测通过）**：`cvd_exam.py` 会话服务（`/api/cvd/exam/start|answer|profile`）——12 题快筛（石原×2 报数字 → 网格×9 三维阶梯点异色块 → 色相排列×1 点击排序）→ triage 分诊 → build_user_profile 档案五件套 + 保守口径 advice；判定全部由 cvd_test 规则引擎完成，会话 30min TTL
- **def 17b 试妆校色联动（2026-09-11 完成，实测通过）**：`cvd_service.recover_true_color`（Lab 空间坐标下降反解"标准视觉等意色"，诚实边界：二色视信息简并、逆映射不唯一，取最小改动解）+ `correct_hex_for_profile`（normal/uncertain 不校正，宁缺毋滥）+ `/api/tryon` 新增 `correct` 参数（默认 true，组合层读档案自动校正，`results.correction` 全程可解释，`query.hex_requested` 留痕用户所选）；tryon 页校正状态条 + **隐藏 details 标签**（防误触，含关闭开关）；工具⑤ 供 AI 总结话术
- **def 17d 数据外置·职责分离版（2026-09-13 二次重构，实测通过）**：用户确认 GB 命名与官方匹配**职责分离**——`data/shades/gb_names_16.json`（`generate_gb_names_16.py` 产物，**纯 GB 命名** 4096 条）+ 官方匹配由 coverage16 端点**运行时**从 shades.json 逐点 ΔE00 取最近（官方库扩充自动跟随，无需重跑生成脚本；按官方库条数缓存，二次请求 137ms）。**官方匹配修正**：Lab 欧氏 argmin → **ΔE00 全量取最小**（深色区两者背离：#000088 欧氏最近樱花粉 dE00=44，ΔE00 最近干枯玫瑰 32.26）。GB 命名修正：HSV 色调替代 Lab 色相角（深蓝不再误判红紫）+ 修饰语互斥（无"鲜暗"矛盾）。数据文件不含官方匹配（用户规则：非官方命中名称输出空）。SQL 备忘：4096 行 JSON 足够；色号库/产品数据增长后 SQLite（Python 内置）为自然升级路径
- **def 17d/17e 反馈修复轮（2026-09-13，全部实测）**：① 色号查询结果官方有/无徽章（dE≤1.0）② 覆盖检查 16³=4096 采样点 vs 官方库（可视化：B 通道 16 层网格 + 绿框有/红框缺 + 点选详情 + 命名清单视图 + CSV 导出）③ **GB/T 15608 近似命名引擎**（10 基本色调 + V/C 标号 + 中文色名；修 HSV 色调替代 Lab 色相角——深色区 Lab 会把蓝判成紫红；修"鲜暗"修饰矛盾）④ **数据外置**（`data/shades/color_coverage_16.json` + `scripts/generate_color_coverage.py` 生成器——用户明确要求命名/匹配数据不内联代码；库扩充后重跑脚本即刷新）⑤ **官方匹配修复**：Lab 欧氏 argmin → **ΔE00 全量取最小**（深色区两者背离：#000088 欧氏最近樱花粉 dE00=44，ΔE00 最近干枯玫瑰 32.26）⑥ t1 双请求解构 bug 修复（safe 包装未解构 getJSON 的 {j,ms}）⑦ 非官方命中名称输出空（用户规则）⑧ 覆盖网格点选详情。实测：黑色查询全链正确 + 覆盖率 0.1%（20 条库缺口暴露 → 图片库扩充目标清单 CSV）
- **def 20 调度工具（2026-09-11 完成，实测通过）**：navigate_tool（5 页白名单）+ agent_loop 顶层 action 提升 + prompt 流程引导状态机 + 去 emoji；实测"带我去色盲校验" → 16.4s 返回正确 action
- **流程联动（2026-09-11 用户定稿）**：全站用户旅程 = 色盲测试 → 色盲校色选择 → 试妆；测评完成 → AI 引导校色 → 校色完成 → AI 引导试妆（引导状态机见 5.6）。**流程纪律已代码化（实测）**：`/api/cvd/exam/calibrate`（mode: correct/simulate/off）写入档案的 calibration 状态；`/api/tryon` 只消费该状态——未校色直接试妆 → 如实提示"尚未完成校色步骤"，simulate/off 模式 → 色号不反解
- **R-06 全站配色联动（2026-09-11 用户新增，演示爆点）**：校色完毕后整站配色随之修正——CSS 变量（--ac/--ac2/--tx/--bd/背景渐变三色）已全站集中管理，JS 端以 Machado 矩阵对关键色做 daltonize 变换写回变量，网页本身即"校色效果"的活演示；附"模拟模式"开关（正变换，让正常视觉用户看到色盲用户眼中的网站 = 共情演示），答辩双层故事：校色是服务，模拟是共情。**开关形式 2026-09-11 用户确认：两种模式都做，交由用户自行选择切换**
- **R-07 色号体系合规策略（2026-09-13 定稿）**：潘通编号体系/数据库/商标受知识产权保护，不引入；颜色数值本身（sRGB/Lab）是物理事实不受版权保护。四层免费合规方案：① **自建色号**（shades.json 自拟中文色名，美妆行业惯例——Dior 999 等本就是品牌自建体系）② **CIE 数值体系**（Lab/LCh/CIEDE2000 开放标准 = 准确性锚点，项目底座）③ **GB/T 15608 中国颜色体系**（国标全文免费公开，标注标准号可商用引用）④ **ISCC-NBS 色名法**（公有领域 267 区块，centroid 数据开源）——扩充管线（图片库 → extract → shades.json）自动挂"标准色名 + 自拟色名 + Lab/LCh"三重身份；品牌单品色号 RGB 作事实引用，不复制数据库编排；商用前 IP 律师复核。**口径确认（2026-09-13 用户定稿）：现阶段标注体系以 GB/T 15608 为准，PPT/答辩需说明此选择；实际商业落地时切换到接受度更广、更权威专业的色卡库（如获取授权的 Pantone/NCS）**

### 5.4 def 18 · RAG 配色改造：AI 自动操作色盘（保留用户权限）
- 数据侧（用户收集）：知识库补充**颜色搭配语料**（搭配组合/场景/适合肤色），量越大越好
- 检索侧：kb_search 命中搭配类语料时**只返回搭配数据本身**（颜色组合、场景、条件），不带任何观点——观点留给 AI
- AI 侧：大脑基于搭配数据思考配色 → function calling 输出**具体色号 JSON**（支持多部位一次给出）
- 前端（tryon 子页）：AI 返回的色号**自动填入**对应部位表单，可一键直接试妆；用户随时可改写/清空/撤销——AI 能自己操作色盘推荐，最终决定权在用户；填充动作由**伴随 AI 悬浮窗**执行（见 5.6，对话与操作同一入口）
- 落点（动工时定）：agent_reply 返回结构扩展 `recommendations=[{region, hex, reason}]` + action 指令（与 def 20 共用同一套 action 通道）
- **def 18i · 对比库（2026-09-19 完成，用户澄清后定稿）**：产品库橱窗新增「对比库 · 全商品色板」窗口——把**全部商品已有颜色**（唇 20 / 粉底 168 / 眼影 12 / 眉 5 / 腮红 5，去重 **209 色**，按明度暗→亮排序）汇成一个色板；每色块**悬停浮出商品清单**（跨品类：如 #3E3A39 同时列「眼影 1 · 碳黑 / 眉妆 1 · 碳灰棕」），色块**绿框 = 官方色库（GB 16³）覆盖**（精确命中格点或邻近 8 格 dE≤1.0，与 def 17e「官方有/无」徽章同语义，当前 10/209）。实现：`products_service.compare_library()`（hex→商品反转索引 + `_official_cover` 判定）+ `GET /api/products/compare` + products.js `openItem` compare 分支（只读色板）+ `.sw-off`/`.sw-multi` 样式；官方色卡图入 assets。冒烟：HTTP 200、count=209、official=10、multi=1 ✓

- **def 18j · 查询卡精简 + 已导入商品色并入官方判定库（2026-09-19 完成，用户需求）**：① palette 页色号查询卡**删「最近替代」列表与「全库精确匹配」段**——查询只对官方判定库做判定（有 → 列命中色号；无 → 如实标注可申请定制）；② **判定库扩容**：`search_shade_tool` 合并已导入商品色（粉底 168/眼影 12/眉 5/腮红 5，共 190 色 + 官方唇色 20 = **210 条**）参与同一次 CIEDE2000 最近邻排序，商品色精确命中 dE=0 → has_official=true（修复"已导入颜色在官方库压根没有匹配"）；实现：search_shade.py `_imported_rows()`（importlib 直载 products_service，失败自动退回纯官方库）+ 响应新增 `pool_size`；命中条目带 `imported:true` 与「已导入商品 · 品类 · 品牌」标注。对比库绿框维持 GB 16³ 原生覆盖语义（与判定库扩容区分）。冒烟：#FADCC8/#7B3C11 均官方有（dE=0）、#FF4D6D 唇色不回归 ✓
- **def 18k · 全域色库升级 256³ 真全覆盖（2026-09-19 完成，用户需求）**：用户指出 GB 16³=4096 采样格点的 hex 全是 **#AABBCC 型重复结构**（每通道只取 0x00,0x11,…,0xFF），"这不叫全覆盖"——全域库改为 **256³ = 16,777,216 色真全覆盖**（任意 #ABCDEF 组合都是成员）。落盘 16.7M 条不现实（约 1.5GB），**全域库算法化**：由 GB/T 15608 标号算法（`gb_color_name`）对任意 RGB 即时计算标号+中文名，不再依赖采样文件。查询卡两层信息：①「全域色库有此颜色 ✓（16,777,216 真全覆盖）」恒真（in_universe，附 GB/T 标号）②「商品可提供性」（官方唇色+商品色 210 条 dE≤1.0，has_official）——有则列命中清单，无则提示可定制。修复：`_imported_rows()` 直载链路补 `sys.path` 注入（products_service 内部 `from agents.tools...` 包导入在裸直载下 ModuleNotFoundError → 合并静默失效，实测 #7B3C11 曾退回 20 条唇色库）。gb_names_16.json 保留为「标准样册离散格点」数据源（覆盖检查/精确命名加速）。冒烟：#ABCDEF 全域命中+标号 10BG 8.1/8.3 浅蓝绿、#7B3C11 全域+商品双命中（dE=0）✓
- **def 18l · palette 页只保留一个全域色库（2026-09-19 完成，用户需求）**：用户指出**两个色库定位冲突**（覆盖检查卡的"官方库=16³=4096 aabbcc 格点" vs 查询卡的"全域 256³"）且**工具③没用**——①删「覆盖检查」卡（16³ aabbcc 网格可视化）+ `/api/tools/coverage16` 端点 + `coverage16_tool`；②删「工具③ palette_search」卡 + `/api/tools/palette_search` 端点 + registry/prompt 的 palette_search_tool 注册与描述 + **agents/tools/palette_search.py 整文件**；③顺带删「工具② kb_search」死卡（`/api/tools/kb_search` 端点在 main.py 从未存在，点了必 404）+ js 死代码（t2/t3/swatch/render）；④查询卡内嵌**全域渐变墙**（24×12 紧凑 RGB 采样，色值全为 #ABCDEF 型任意组合——替代被诟病的 aabbcc 网格视觉）。palette 页最终 = **全域色库查询（256³）+ 全域渐变墙**，单一色库定位。冒烟：查询 200/全域命中、palette_search 与 coverage16 均 404（已删）、页面无死卡 ✓
- **def 18m · 全域色盘全部可显示（2026-09-19 完成，用户需求"要全部显示，可用滑轨移动看色盘"）**：查询卡的 24×12 采样示意升级为 **canvas 全域色盘**——256×256（横轴 R 0→255 · 纵轴 G 0→255，image-rendering:pixelated 逐像素）+ **B 通道滑轨**（0-255 共 256 层），256 层 × 65,536 色 = **16,777,216 色全部可显示**（真正的全域全覆盖，非采样）。交互：拖滑轨逐层浏览；**点击色盘任意色 → 自动填入查询框并触发查询**；查询完成 → 色盘**自动跳到该色所在 B 层并画框高亮**（白/黑描边自适应）。实现：纯前端 ImageData+putImageData（每层 65,536 像素即时重绘，零后端开销）；`window.__uniSetMark(hex)` 由 t1 查询成功后调用。冒烟：esprima/HTML 配对全绿、查询 200、页面含 canvas+滑轨+def18m ✓
- **def 18n · 色盘防跳位 + 商品色上盘（2026-09-19 完成，用户反馈）**：① **点击色盘页面跳动修复**——根因 = 查询结果区（s1res）在色盘上方，每次点色盘触发查询 → 结果内容撑高把色盘推下去；重排结构为「色盘+滑轨 → 结果区（min-height:140px 固定占位）」，结果更新只在色盘下方发生，色盘纹丝不动；② **已导入商品色上盘**：拉取 `/api/products/compare`（209 色）构建 hex/B 层双索引——当前 B 层内的商品色画**绿框**标记，**hover 显示归属**（如「#3E3A39 · 已导入商品：眼影 · 眼影 1 · 碳黑 / 眉妆 · 眉妆 1 · 碳灰棕」），滑轨旁新增「跳到商品色所在层」下拉（列出所有含商品色的 B 层及色数，选中即跳层），本层商品色计数实时显示。实现：纯前端 Map 双索引 + ImageData 重绘后叠画 strokeRect；商品色加载完成后自动重绘当前层。冒烟：esprima/配对全绿、compare 209 色供数据、页面 unijump/min-height/def18n ✓
- **def 18o · 商品色层下拉风格统一（2026-09-19 完成，用户反馈"展开后的栏要和前端风格统一"）**：原生 `<select>` 的展开列表是 OS 渲染（白底），CSS 无法定制——改为**自定义下拉面板**：触发按钮（.ujbtn，玻璃底+主题边框）+ 绝对定位面板（.ujpanel，深紫底 rgba(24,16,28,.96) + backdrop-filter 毛玻璃 + var(--bd) 边框 + 零圆角 + 阴影），项（.ujitem）hover 用品牌色 rgba(229,71,109,.18) 高亮，左"B=层号"右"色数"；点击项跳层收起、点击面板外自动收起、面板内点击不冒泡。样式内联在 palette.html `<style>`（palette 专属 .uj* 命名空间，不动共享 style.css）。实现要点：window.ujToggle 挂全局供内联 onclick；构建面板项替代 createElement("option")。冒烟：esprima/配对全绿、无 `<select>` 残留、查询/compare 200 ✓
- **def 18p · 附近层黄框导航 + < > 微调（2026-09-19 完成，用户需求"附近 5 层加黄框判断最近颜色在哪"+ "B=xxx 右边加 < > 微操"）**：①全域色盘叠加**附近层商品色黄框**——本层绿框之外，B±1 层画**黄实线框**、B±2 层画**黄虚线框**（canvas setLineDash，绘制后复位），用户拖滑轨时即可预判"附近哪一层、哪个 (R,G) 位置有货"，自己移动滑轨就能到；越界层自动跳过；信息行同步显示「本层 N（绿框）· 附近 ±2 层 M（黄框：实线=±1，虚线=±2）」。②`B=xxx` 右侧新增 **`<` / `>` 微调按钮**（.ujbtn 同款风格，title 提示），uniStep(±1) 钳位 0-255 逐层步进——滑轨粗调 + 按钮细调。冒烟：esprima/配对全绿、页面微调按钮与 def18p 就位、查询 200 ✓
- **def 18q · 全屏选色剧场（2026-09-19 完成，用户需求"加放大到全屏的按钮 + 支持自己调整色盘大小放大查看"）**：色盘区包进 `unihome/uniwrap`，新增「⛶ 全屏选色」按钮——打开 fixed 全屏层（深紫毛玻璃），**色盘节点整体搬家**到全屏槽位（appendChild 移动节点，事件/状态零丢失，关闭移回卡内），全屏下 canvas 自动放大（去 512px 上限，min(92vmin,980px) 正方形）。**两种调大小方式**：①**滚轮缩放**（1×~32×，以鼠标位置为中心缩放，transform: scale+translate 实现，ImageData 256×256 分辨率不变、像素锐利）；②**拖拽平移**（z>1 时按住拖动，与点击取色以 4px 位移阈值区分互不误触）；另配 −/重置/＋ 按钮与倍率显示（100%~3200%）。选色映射用 getBoundingClientRect（自动适应 transform）——缩放平移后点击取色依旧精确。Esc/✕ 关闭。卡内小色盘行为不变。冒烟：esprima/配对全绿、页面全屏层/按钮/def18q 就位、查询 200 ✓
- **def 18q-fix · 色盘全黑修复（2026-09-19，用户报"色盘改炸了"）**：Edge headless `--dump-dom`+console 捕获定位真凶——`Uncaught ReferenceError: img is not defined`（palette.js draw 内）：此前多轮 IIFE 开头编辑把 **`const ctx = cv.getContext("2d")` / `const img = ctx.createImageData(256,256)` 两行丢失**，draw() 一执行即抛 → canvas 透明全黑、unipick 不更新、jumpPanel 靠 async 分支侥幸工作。修复 = 补回两行；顺带修两处确定性隐患：① t1 中 `__uniSetMark(j.query.hex)` 移到 `!j.ok` 判断之后（异常响应不再 TypeError）；② `uniFs(false)` 回位改为 `home.insertBefore(wrap, home.children[1])`（appendChild 会把色盘塞到滑轨/unipick 之后导致开关一次布局即乱）。验证手段升级：**Edge headless 截图 + console 日志捕获**纳入色盘类改动的验收流程——修复后截图确认彩虹渐变、绿框 2、黄框 10（实线/虚线）、信息行计数全部正常 ✓
- **def 18r · 查询结果去恒真行 + 商品色自动吸附（2026-09-19 完成，用户需求"不要显示全域色库是否有；绿色（商品色）允许自动吸附，显示商品颜色是否有这个颜色"）**：①查询结果**删「全域色库有此颜色 ✓（16,777,216 真全覆盖）」恒真大绿条**（全域库语义下恒真、零信息量）——结果精简为「GB/T 15608 标号近似命名行 + 商品可提供性」：有商品色 → 命中清单（徽章文案"官方有 ✓"→"**商品有 ✓**"）；无 → 粉框提示「暂无商品色可提供——可走定制申请」；②**色盘点击自动吸附**：新增 `snap(b,r,g)`——在当前 B 层绿框商品色中找 (R,G) 欧氏最近者，距离 ≤ **12 色阶**即吸附到该商品色的精确 hex 再查询（商品色很小点不准，靠近就能选中）；hover 同步吸附预览「吸附 → #XXXXXX · 已导入商品：…」；吸附命中后查询结果即显示该商品归属（"商品有 ✓"+品牌/品类清单）。unipick 说明文案同步更新。验证：esprima 全绿、headless 截图渲染无回归（渐变/绿框 2/黄框 10/console 无报错）✓
- **def 24 · 全流程测试三修复（2026-09-19 完成，用户全流程手测反馈）**：①**AI 答问纪律**——用户问"这个系统怎么用"却被抢跳导航/推测评（navigate_tool 触发条件过宽："话题属于某页职责时调用"把咨询当导读）→ prompt.py 三处收紧（_CHAT_HEAD navigate 段 / TOOL_DESCRIPTIONS / _CHAT_TAIL 新增"**先回答，再引导**（最高原则）：问题本身必须先直接回答，禁止用跳页代替回答"），复测同问题零工具调用、直接给出四步流程完整回答 ✓；②**石原题补三轴**——用户指出"缺蓝绿测试数据"：出题组合从 deutan/protan×5 扩为 **deutan×4+protan×4+tritan×2**（triage._vote_type 本就支持 tritan 双证据，天然兼容）；ishihara.py 配套升级——`_rand_base_rgb` 按 kind 分轴选色相区（tritan 用蓝黄重灾区 75-105°/200-290°）、混淆对构造加**双指标择优**（dE_n≥11.5 且 dE_s 达标，48 base × 全方向球面 α×θ 扫描 325 方向按残差比 dE_s/dE_n 选方向再定步长）；**模型边界如实记录**：Machado tritan 矩阵 σ_min>0 无精确混淆方向（deutan/protan 精确秩亏 dE_s=0.00），dE_n≈12 时 dE_s 物理下限≈1.9-2.2，验收口径 dE_s≤2.5（仍处 confuse<5 区间），实测 12 seeds max 2.49 ✓；③**排列题槽位一行**——15 槽×48px 固定宽超面板宽被 flex wrap 成两排（用户："得排成一排，不然一定有偏差"）→ hueslots 改 grid repeat(15,minmax(0,1fr))、槽 aspect-ratio 弹性、chip fluid 化（槽内 width:100%），huepool nowrap+横向滚动，fixture 截图验证 15 槽完整一行 ✓；④**校色开关踢回 bug**——进页时无档案 hasProfile="0"，做完测评后该标记**未更新**，点顶部开关走"暂无档案"分支 → showTab("exam") 跳回测评第一步且不执行校色 → renderProfile 时即置 hasProfile="1"（档案生成即解锁），修复后开关直接执行 doCalibrate（CVDTheme 全站联动+开关状态同步）。验证：py_compile 3 文件、exam start/answer 流转、compare 209、6 页 200、Edge headless 截图无回归 ✓（注意：后端重启后测评档案为内存态会丢失，需重测一次）
- **def 24b · 语音交互两 bug 修复（2026-09-19 完成，用户反馈"点击语音后无法进行下一次操作 + 出错后一点反馈都没有"）**：①**无法二次识别**——`listening` 状态在 `rec.start()` 后置 true 但 onresult/onerror/onend **从不复位**，第二次点击永远走"停止"分支 return（且 rec.stop() 对已结束识别抛 InvalidStateError 被 catch 吞）→ 状态机修复：**onend 兜底 + onresult/onerror/超时/手动停止四处统一 `listening=false; clearTimeout`**，stop 全部包 try；②**出错零反馈**——`rec.start()` 的 `catch(e){}` 空吞（权限拒绝/重复启动无任何提示）→ 异常可见化 addMsg；**aborted 映射原为 null 静默**（Chrome 服务异常中断时按钮亮一下就灭）→ 按 wasListening 区分：意外中断才提示（超时/手动停止已各自提示过不重复）；**no-speech 无映射**（最常见错误走生硬兜底文案）→ 补"没听到说话"人话提示；识别结果为空也静默 → 补"没听清"提示；③**busy 冲突吞消息**——sendMessage 在 busy 时把消息当"停止指令"（abort 当前回答）→ 语音识别结果在 AI 思考中到达会被吞掉还停掉回答 → onresult 里 busy 时只提示"AI 还在回答中"不 abort；④开始聆听新增 meta 提示"正在聆听……说完自动发送，再点一次可停止"（用户知道已开始）。验证：headless 截图 palette 页 AI 悬浮球正常（chatbox IIFE 无语法错误，chatbox.js 含既有 `??` 语法 esprima 不适用）、5 页引用版本统一 bump v=def24 ✓（注：语音端到端需真机麦克风，代码路径已全可见化——任何失败都会有 meta 消息）
- **def 25 · 对比库搬家：产品库橱窗 → 选色页（2026-09-20 完成，用户反馈"怎么给我对比库弄到商品界面去了"）**：对比库（全商品色板 209 色）与选色/商品色吸附同场景，不该占产品库橱窗——① 后端 catalog() 摘除 compare 虚拟窗口（产品库页不再出现对比库卡；/api/products/compare 端点保留继续供数据）；② products.js 删 isCompare 死分支与 CAT_NAME compare 键（顺带补 brow:"眉妆" 显示名）、products.css 删 .sw-off/.sw-multi 死样式，products.js/css bump v=def25；③ 选色页全域色盘标题行新增「▦ 全商品色板」按钮 → 全屏浮窗（.cmp* 命名空间样式内联 palette.html，与 def18o .uj* 同惯例）：209 色块网格、悬停浮出商品归属（多行 products_txt）、绿框=官方库覆盖、Esc/点背景/✕ 关闭、深链 palette.html#cmp 直开。验证：py_compile ✓、catalog 8 窗无 compare、compare API 209 色、esprima（??→|| 预处理）双文件 ✓、headless 截图两页（浮窗渲染+绿框正常 / 产品库无对比库卡）✓
- **def 26 · AI 评测通道打通 + 校色旅程自动化（2026-09-20 完成，用户反馈"AI 评测的通道好像并没有完全打通，是不是接口没串联 + 不要让用户自己点一次分析，分析完成后自动导入校色，用户只点开启校色"）**：①**真凶 = 档案纯内存态**——cvd_exam._PROFILE 重启即丢，前端还渲染着旧档案（重启前画的），此时校色端点报「尚无测评档案」、get_vision_profile_tool 返回 ok:false → AI 退化泛泛而谈（用户看到的"没串联"实为数据源断链，工具/管线本身完好）；②**档案落盘持久化**——_cvd_profile.json 存 app/backend/（_save_profile/_load_profile，_finish 与 calibrate 后即写、启动时恢复，损坏静默跳过），E2E 实测：注入档案→重启→GET profile ok=True（磁盘恢复）→calibrate correct→文件含 calibration ✓，**测评一次终身有效，重启不再要求重测 22 题**；③**校色旅程重排（用户定稿：导入 ≠ 自动开启）**——测评完成 → 先自动调 calibrate("off") 写入校色配置（kind/severity 就绪，试妆通道等开启后才校正）→ 再自动 CBChat.send 通知 AI 读档案总结（消息明确要求引用具体数字 + 告知"配置已导入，点顶部开关即可开启"）→ calstatus 显示「校色配置已自动导入 · 最后一步点顶部开关」；**删除旧逻辑的"自动 apply correct + 开关自动置 on"**——用户唯一动作 = 顶部「校色配色」开关（开启后刷新页面仍自动恢复，因 mode=correct 已持久化）；健壮性：AI busy（cb-send 含 stop 类）自动总结跳过并留提示、send 失败/异常均可见化（不再静默吞）；④prompt.py 全链路话术同步（"测评完成后 AI 自动读取档案并总结，校色配置自动导入，点顶部开关即开启"，替代旧"选择校色模式"表述——旧话术导致 AI 回复"选好之后跟我说一声"与自动化矛盾）；⑤cvd.js v=def26。验证：py_compile 2 文件、esprima（??→|| 预处理）、持久化 E2E（注入→重启→恢复→校色→落盘→清理→干净态）、**AI 通道实弹（POST /api/chat → steps: get_vision_profile_tool:True，回复引用真实数字 5.5/8.0/14.0）**、cvd.html 200 ✓
- **def 27 · 社会视角守门：罕见选色确认 + 主流替代推荐（2026-09-20 完成，用户提出产品哲学矛盾点："绿色盲一辈子没见过绿色，如果他真选了绿口红出去被耻笑反而成为心理伤害——校色更重要的是告诉用户是什么色盲后告诉用户怎么选"）**：①**新端点 POST /api/tryon/shade_review**（app/backend/shade_review.py）——主流性判定（该品类在售板最小 ΔE2000：≤12 主流 / ≤18 边缘 / >18 罕见，诚实声明为项目启发式代理、非行业标准）+ 社会视角翻译（_hue_name 色相/明度/饱和度中文描述，区间命名不装精确色名）+ 社会等效色（correct_hex_for_profile 反解：用户想要的效果在正常视角下的样子）+ **在售主流替代 top-4**（品类在售板按"该用户视角下与所选色 ΔE_sim"升序——语义：换了你看不出区别，别人看到的是正常妆效）；②**触发纪律（用户定稿）**：仅对已建档 deutan/protan/tritan 且 severity>0 且判定 rare 的选色弹确认卡——无档案/主流色**不拦截**；确认卡三要素=告知别人看到的 + 社会等效色 + 推荐色块（点击回填）；**两条路都尊重**：仍用原色→继续（无现货走既有定制面板），换推荐色→直接继续（推荐色来自在售板，无现货直接定制**不再二次询问**）；改色即重新守门（gateKeep region→hex）；③**AI 同步注册 shade_review_tool**（agents/tools/shade_review.py + registry 6 号工具 + prompt.py 工具描述"禁止凭感觉评判颜色"）——确认卡带「问 AI」按钮（结构化数据喂给大脑），AI 独立被问"绿口红合适吗"时也走工具拿数字；④tryon.js 提交口拦截（tyParts 内 review→gate→renderGate→决策后自动重跑）+ tryon.js v=def27。实测：无档案不拦截 ✓、#3F7A3F 绿口红 gate=True min_dE=51.38 社会等效 #796D4F 推荐 复古红棕/干枯玫瑰/珊瑚红/正宫红 ✓、主流 #C2185B min_dE=0 直通 ✓、眼影绿跨品类 gate=True ✓、**AI 实弹 steps: shade_review_tool:True（回复引用 51.38/#722F37/#796D4F 全为代码计算数字）** ✓；修复：_hue_name 色相区间表错位一档（绿 120° 误报青调）、推荐文案中性化（ΔE_sim 大时不说"几乎一样"）
- **def 28 · 石原板生成 v3：全局择优 + 多色族 + 等明度（2026-09-20 完成，用户反馈"石原色的图就不够精准，得优化下生成"）**：make_plate 四处升级——①**全局择优 `_pair_best`**：48 base × 自适应步长不再"首个达标即 break"，deutan/protan 沿零空间方向把正常对比拉到真板水平 **dE_n 20+（实测 25-27，旧版 11.5）**、tritan 由 dE_s≤2.5 物理上限主导（实测 13.8-15.7）；②**多色族 `_family_variants`**：前/背景各 3 变体沿零空间方向"远离对方"侧小偏移（真板多板设计，替换单色对+噪声的"噪点图"观感），族间逐对校验按 cap 严格弃用（色域边缘 clip 会偏离零空间→残差上升），info 增 dE_n_min_pair/n_fg/n_bg/design 字段；③**等明度 `_align_lightness` + Lab 抖动**：两族平均 L* 拉平（明度零线索，差异全在色相/彩度）+ 点级抖动从 RGB±7 改 Lab 空间（L±1.5/ab±1.2 两族同分布，模拟后 region 对比照常坍缩）；④**点阵修复**：底色从灰白 242 改为背景族基色（露底融入背景）+ 半径双峰加大（70% 大点 8-11 / 30% 小点 4-6，直径≥14px 栅格间距）→ 全覆盖无白底 + 数字边界带 P=0.35 翻族犬牙交错（防靠边缘锐度读数）。**意外收获：白底修复后 region_s 全面坍缩**（旧版 242 白底是背景区域里的"第三色"，模拟后拉偏均值）——deutan 0.47-1.31 / protan 0.66-0.79 / tritan 1.80-1.87（物理下限）；selftest 22/22（ishihara 正常可见 18.6 / 隐身 0.6）；三轴样图目检：正常侧数字醒目清晰、模拟侧完全隐身（tritan 余极淡残影为 Machado 矩阵近似秩亏物理边界，口径不变）。接口零变更（make_plate 签名 / cvd_exam 出题 / selftest 断言全兼容）
- **def 29 · AI 陪聊流式改造：SSE 逐字上屏 + 看门狗续命 + config 合并 bug 根治（2026-09-20 完成，用户网页实测"搭配建议"提问 90s 无响应被中断，误判"flash 不适合处理文本、换 pro 太贵"）**：①**真凶三层**——(a) **config.py 浅合并 bug（def 22 起潜伏）**：`cfg.update(user)` 让 secrets 的 providers 整体顶掉 _DEFAULTS，per-provider 合并又在"已丢失默认值"的版本上做 → **thinking:disabled 从未真正下发**，GLM 默认深度思考（诊断实锤：连"一句话介绍"都 200 帧 reasoning_content）→ 长题 60-90s 思考+生成必撞死线；(b) **非流式黑箱**：llm_client urllib 同步等完整 JSON，首字延迟=全部生成时间，用户全程只见 thinking…；(c) **前端 90s 硬死线**：AbortController 掐断后后端还在跑（白烧 token）。修法=不换模型不花钱：②**config 深合并修复**（providers 以默认值为底逐 provider 合并，thinking disabled 真正生效）；③**SSE 流式管线**：llm_client.llm_chat_stream（OpenAI 兼容 SSE 逐帧解析 + tool_calls 分片按 index 聚合 + 每 chunk 回 ping 心跳）→ agent_loop.agent_reply_stream（yield status/delta/tool/replace/done 事件；出口安检流式下全文攒完再扫、命中发 replace 整条替换——防泄密硬门不因流式绕过；MAX_ROUNDS/入口安检纪律不变；_lift_action/_run_tool_call 抽公共函数防双版本漂移）→ main.py POST /api/chat/stream（StreamingResponse 同步 generator 自动 iterate_in_threadpool）；④**前端 chatbox.js 流式渲染**：fetch ReadableStream + SSE 帧解析、delta 逐字上屏、tool 轨迹实时显示（done.steps 不再重复打印）、done 统一入档 msgs（流式气泡 DOM 先行不进档，防断流留半条记录）、90s 硬死线→**60s 无进展看门狗**（任收帧即续命——实测帧间最大空窗 8.8s，永不误杀）、中断保留已生成部分并入档+如实说明、状态行 cb-thinking 手动创建（**顺手根治五处 querySelector('.cb-thinking') 死引用**——旧版 Thinking 行从不被移除一直残留界面）；⑤**兼容性**：非流式 /api/chat 与 agent_reply 原样保留（内部调用/回退路径）、done payload 与旧返回形状完全一致（cvd.js 自动总结 CBChat.send 零改动兼容）、5 页 chatbox.js?v=def29。实测：py_compile 4 文件、esprima（??→|| 预处理）、实弹复现用户原题——status 0.02s → 工具轨迹实时（foundation_search/recommend_shade）→ 正文 491 字 446 delta 帧 → done，帧间最大空窗 8.8s（60s 看门狗安全）✓；诚实边界：首字 ~60s 的剩余大头是 2-3 轮工具决策的 GLM 侧延迟（每轮 LLM 往返 ~20s，模型行为非代码问题），流式已把"黑箱等待+必断"变为"全程有反馈+不断"；若需更快可切 deepseek provider（secrets 改 provider 一行）或收紧 prompt 减少工具轮次
- **def 30 · 校色反馈诚实化：uncertain 档案"开关无效"之谜根治（2026-09-20 完成，用户真机反馈"校色系统启动后网站没什么变化，检查下前端是否接通"）**：①**诊断定性：前端接通、数学恒等**——用户档案 calibration.kind="uncertain"，theme_cvd.js 加载/开关时 `M_FULL[cal.kind]` 无 uncertain 键 → applyTheme 直接 resetTheme（原色）；后端同口径（correct_hex_for_profile 对 uncertain 返回"档案类型无需校正"）——整条校色链路对 uncertain 用户静默恒等，且 doCalibrate 文案对任何类型都谎称"全站配色已联动"（对 uncertain 是假话）→ 用户以为坏了；②**科学口径决策：不做猜测性补偿**——uncertain 时 daltonize 补偿方向可能错（把"看不清"变成"看错"），与诚实边界哲学一致，保持不补偿，改为反馈透明化；③**修复四处**：theme_cvd.js applyTheme 返回 {applied, reason}（kind 不支持 → applied:false + reason:"kind_unsupported"，向后兼容）；cvd.js doCalibrate 按返回值分支——uncertain 时显示「校色配置已保存 + 未定型不做页面颜色补偿的原因 + 测出明确类型可看效果、可点重新测评」（替代假话）；renderProfile 页面加载时同样补说明；AI 自动总结通知文本加第四点（uncertain 必须如实说明开关后颜色不变及原因，声明"这不是故障"）；prompt.py 全链路话术同步；④数学验证：deutan/protan/tritan 明确类型下 --ac #e5476d → #ff0071/#ff006c/#ce5c7f（变化显著可见，引擎本身工作正常）✓；版本 theme_cvd.js/cvd.js bump v=def30（5 页），esprima 双文件 + prompt.py py_compile ✓
- **def 31 · 照片本地缓存 + AI 会话空对话复用（2026-09-20 完成，用户需求"添加照片的缓存；聊天框每次刷新新建对话会撑满列表——新对话未被使用就直接续用，直到被使用过再说"）**：①**试妆照片 IndexedDB 本地缓存**——tryon.js 新增 idbOpen/idbGet/idbSet 极简封装 + tyPhoto 状态 + dataURLtoBlob（提交 FormData 用）；选照片即写缓存（key=photo，原图 dataURL，IndexedDB 配额远大于 localStorage），页面加载自动恢复上次照片（upzone 预览标注"已恢复上次照片"，点击随时更换且新照片覆盖缓存）；tyParts 提交改为 `files[0] || dataURLtoBlob(缓存)`——刷新/关页后不重新选文件也能直接试妆；隐私：只存浏览器本地，不经服务器；②**AI 会话空对话复用**——newConv 统一入口改造（刷新自动建 + 手动点 + 都走它）：存在"未使用过"的会话（msgs 为空）→ 直接续用最近的一个（convs 按创建时间升序取尾），多余空会话顺手清理（空会话无数据，删除零损失）；生命周期 = 新建 → 发过消息（被使用）→ 下次新建才真正开新会话；修复"每次刷新 +1 个空新对话撑满 ≤5 会话列表"的历史行为；delConv 兜底空会话与复用逻辑天然一致；③版本 chatbox.js/tryon.js bump v=def31（chatbox 5 页 + tryon.html），esprima 双文件（??→|| 预处理）✓；无后端改动，纯前端






### 5.5 def 19 · 多子页架构改造（先于 5.1-5.4 动工）
- index.html 瘦身：产品介绍 + 四个入口卡（01 选色 / 02 试妆 / 03 色盲校验 / 04 AI 陪聊）
- 子页规划：`palette.html`（工具①③选色）/ `tryon.html`（试妆全家桶 + 肤色分析 + AI 自动填充）/ `cvd.html`（模拟预览 + 色对校验 + 测评全链）——**AI 不设独立子页**，以伴随 AI 悬浮窗内嵌所有子页（R-05，见 5.6）
- 公共：style.css 抽离（毛玻璃主题变量与组件样式，保持零圆角规范）+ 每页统一顶部导航（含返回主页）
- 顺序：先立骨架（页面路由 + 公共样式），再按 tryon 页（5.1→5.2→5.4）与 cvd 页（5.3）分头填充

### 5.6 def 20 · 伴随 AI 悬浮窗（内嵌所有子页 + 自动调度页面）
- 形态：右下角悬浮对话窗（毛玻璃、零圆角、可展开/收起），由 chatbox.js 动态注入 DOM，所有子页共享一套代码；对话历史存 sessionStorage，跨子页跳转后自动恢复上下文；**对话生命周期（用户 2026-09-11 定稿）：刷新页面（F5/reload）= 清空对话，切换子标签 = 保留——以 Navigation Timing type 区分（reload 清 / navigate 留）**
- 能力一：全程陪聊——复用 /api/chat 与现有 agent_loop，四步流程任何一步都可以问
- 能力二：**自动调度页面**——AI 理解用户意图后跳转到对应子页并可带参数（如"这个颜色在色盲眼里什么样" → 跳 cvd.html 并预填色号；"帮我配一套眼妆" → 跳 tryon.html 并自动填充，联动 def 18）
- 能力三（2026-09-11 用户定稿）：**流程引导状态机**——AI 感知用户所处阶段（未测评 / 已测评未校色 / 已校色未试妆），在当前界面直接文字引导下一步 + action 跳转（测评 → 校色 → 试妆）；后端 agent prompt 注入流程状态，agent_reply 扩展 action（navigate 通道已预留）
- 落点（2026-09-11 确认：**一步到位，不走"先语义分析 → RAG 执行"两段式**）：navigate(page, params) 注册为轻量工具，走现有 registry/dispatch 通道——dispatch 识别后不执行数据逻辑，转成返回结构里的 `action={type:"navigate", page, params}` 交给前端执行；与 5.4 的 recommendations 共用同一套 action 通道。决策理由：调度常依赖工具执行结果（先查知识才知道引导去哪），两段式切断"工具结果→决策"链且延迟翻倍；RAG（kb_search）是大脑的知识源（服务"AI 说什么"），不是页面路由器；5 页封闭集合用 prompt+流程状态机直接选页即可
- 安全阀：dispatch 层对 navigate 做**页面白名单枚举校验**（5 页硬编码，非法值拒绝）——决策交给 LLM，合法性交给代码（铁律同源：数字由代码算，AI 只引用；路由由 AI 决策，边界由代码守）
- 边界：AI 只发起跳转/填充，表单最终提交权在用户（R-05 原则）；调度是前端行为，不碰后端数据流；AI 调度动作在前端轨迹区可见（可解释）

### 5.7 面试问答稿（正式交付物，2026-09-08 新增）
- 动机：本项目是用户简历的核心项目经历，用户必须能亲自讲清每个模块——既防"AI 代写"面试穿帮，更倒逼真正的理解
- 形式：AI 按面试官视角出 20 问（项目介绍 → 技术深挖如 CIEDE2000/Machado/RAG → 架构取舍如 R-04/R-05 → 失败与重做），每问配答案要点 + 追问链；随各 def 交付滚动更新
- 用户动作：把答案消化成自己的话对着讲；AI 可随时扮演面试官模拟追问（红队训练）
- 进度（2026-09-11）：**0/20，def 17 收口后出第一批 8 问**。已积累素材：① navigate 一步到位 vs 两段式的架构决策（5.6）② def 17b 意图反解与信息简并的诚实边界（5.3）③ R-06 双模式开关（服务+共情）④ 规则引擎 vs LLM 判定的分工（triage 设计要点）⑤ selftest 22/22 的锚定体系 ⑥ 五件套契约与轨迹可见性 ⑦ None 覆盖 bug 的实测价值案例 ⑧ 产品库=AI 调度落点的产品思维

### 5.8 def 21 · 语音输入与无障碍化妆愿景（2026-09-13 新增）

- **R-08 产品价值观（用户 2026-09-13 定稿，答辩核心叙事）**：盲人化妆是为了**得体**（社交尊严），而非自我视觉确认；拒绝把盲人克制在"盲人不需要化妆"的概念上；"盲人无法看到自己的妆容"是当下不可解的问题，**未来脑机接口是技术出口**（PPT 技术路线图一页）。叙事纪律：尊严视角而非怜悯视角
- **def 22 反馈修复·AI 入口消失（2026-09-13/14，用户报"气泡消失了"）**：根因 = chatbox.js 重构时锚点法残留**多余的 `})();` 收尾**——JS 语法错误 → 整个 IIFE 不执行 → AI 球（入口按钮）不注入。**根因暴露方式**：此前无 JS 语法验证手段（环境无 node）→ 本轮引入 **esprima（纯 Python JS 解析器）+ `??`→`||` 预处理**验证法，秒定位 Line 384 多余收尾。**自检清单新增**：每次 JS 改动后必跑 esprima 语法验证（约 2 秒）
- **def 22 · AI 悬浮窗界面重构（2026-09-14，用户定稿，全部实现）**：① 用户消息右对齐**圆角气泡**（带边框透明底，该区域允许圆角）+ AI 回复浅底圆角 ② 输入区统一：**SVG 麦克风圆标 + 输入框 + SVG 纸飞机发送**（去 emoji 用内联图标）③ **思考中锁定输入区**（防串台：输入禁用+半透明，发送按钮变停止图标）④ **90s 超时 AbortController**（超时提示可重发）+ **思考中点发送=停止**（abort 中断输出）⑤ **左侧对话选择栏：最多 5 会话，新建自动顶替最早**（标题=首条消息前 14 字，sessionStorage 持久，刷新全清规则不变）⑥ **语音修复**：onerror 人话提示（Chrome 网络受限→建议 Edge；权限拒绝→引导授权）+ **识别超时阈值 10s**（用户要求的阈值落地）。面板加宽 430px，对话栏 76px
- **def 21 功能（2026-09-14 实现完成，待手测）**：**语音闭环双通道**——输入：Web Speech API SpeechRecognition（中文 zh-CN，"语音"按钮按下说话松开识别，识别即发送；不支持的浏览器自动隐藏）；输出：**SpeechSynthesis 朗读 AI 回复**（"朗读:开/关"开关，默认关、localStorage 记忆，朗读时去 markdown 符号；关闭即停止播报）。均浏览器原生零后端依赖。盲人用户由此可全程语音完成"选色咨询 / 定制申请 / AI 引导"——**看不见，但完整参与色彩决策**（R-08 的第一个落地）
- **排期**：def 15 之后插入，约半天（前端 30 行 + 兼容性实测）
- **def 18 扩展（同日用户想法，技术杠杆大）**：RAG 语料从"颜色搭配"扩展为**"妆容×穿搭整体形象"**（用户："好的化妆应该和好的衣品搭配是同一套"）——AI 输出从色号 JSON 扩展为整体形象方案（妆容色号 + 穿搭色系/风格）；展示落点 products.html。用户作业变更：搭配语料收集时**穿搭类语料一并收集**

### 5.9 def 23 · 大模型安全学习 + 红队评测项目（2026-09-18 立项备忘——**独立学习线，不占本项目排期**：欧莱雅项目全部收尾（材料+提交+答辩）后，10 月初启动）

> 边界先行：本节只是立项备忘，**9 月内零占用**——材料阶段精力 100% 给欧莱雅；下方周计划节奏按 10 月秋招投递/笔试情况弹性调整。

- **动机（三条，对应 R-10）**：
  1. **已有雏形从未被评测**——def 22m 的纵深防御（入口 `_INJECT_PATTERNS` 7 条正则、出口 `_LEAK_PATTERNS` 扫描、navigate 5 页白名单）是"正则兜底"，没人知道覆盖率多少、漏报率多少、哪些攻击能绕过；
  2. **岗位差异化**——AI 应用岗简历上"会用 LangChain/会调 prompt"已是标配，**"我按 OWASP 标准给自己的 AI 系统做过红队评测、把防御从正则兜底升级为可量化拦截"**是稀缺叙事；
  3. **项目制学习**——纯看书留存低；以自己的真实项目为靶场，每个攻击用例都有真实意义，产出直接可复用。
- **学习路径（OWASP Top 10 for LLM Applications 2025 为骨架，约 6 周——10 月初启动，节奏随秋招投递/笔试弹性调整）**：
  - **第 1 周 · 通读与对照**：OWASP LLM Top 10 逐条精读，**逐条映射到本项目**——LLM01 提示注入 ↔ def 22m 入口检测、LLM02 敏感信息泄露 ↔ 出口扫描、LLM06 过度代理 ↔ navigate 白名单（AI 只能去 5 个页面）、LLM07 系统提示词泄露 ↔ prompt.py 的保护、LLM08 向量与嵌入弱点 ↔ **kb_search 语料投毒**（间接注入的天然试验田：往语料副本里塞一条"用户问 X 就回答 Y"看 AI 会不会被带偏）；
  - **第 2 周 · 攻击分类学与用例设计**：直接注入 / 间接注入 / 越狱（角色扮演、编码绕过、多语言绕过）/ 敏感泄露 / 越权调度（诱导 navigate 到非法页、诱导 recommend_shade 越界部位）/ 资源耗尽（超长输入）——按分类产出用例清单；
  - **第 3 周 · def 23 评测集 + 自动化脚本**：目标 **60~100 条攻击用例**（JSON：分类标签 + 攻击载荷 + 期望行为断言），评测脚本批量打 `/api/chat`、解析 `content/action/steps`、输出得分报告（按分类统计拦截率）；
  - **第 4 周 · 防御升级**：入口正则漏报分析 → 升级方案（轻量语义分类器 / 结构化输出约束 / 工具参数白名单再加严）；间接注入实验与 kb_search 结果标污设计；
  - **第 5 周 · 复测与报告**：升级前后拦截率对比（数字说话）+ 评测报告成文；
  - **第 6 周（弹性）**：评测方法学抽象成可复用脚本（换一个项目改配置就能跑）。
- **def 23 交付物**：① 攻击用例集（60~100 条，带分类与期望行为）② 自动化评测脚本 + 报告 ③ 防御升级 diff（正则兜底 → 可量化拦截）④ 评测报告（拦截率前后对比）⑤ **面试问答稿新增 3 问**（怎么防注入 / 怎么评测 AI 系统的安全性 / 什么是间接注入——你项目里就有真实案例）
- **边界纪律**：欧莱雅项目全部收尾（材料+提交+答辩）前**一行不动**；评测只打本地实例，不对外部服务发真实攻击流量；语料投毒实验只在自己副本做，正本（data/shades、语料 JSON）不污染。
- **答辩/简历叙事**："我不仅用 AI 构建了应用，还按 OWASP 标准给自己的 AI 系统做了红队评测——发现并修复了 X 处绕过，把恶意注入拦截率从 Y% 提升到 Z%"——这是泡沫环境下"AI 系统的可靠性与安全"这一成本项叙事的正面回答。
- **后置项（写进 PPT"规划中"，不进当前排期）**：AI 图像修图（自动祛瑕/磨皮——BiSeNet mask + 保边滤波技术可行，但效果调优成本高，hackathon 期内不做）

### def 32 ✅ 全站硬编码品牌色收敛为相对色语法（校色/模拟真正"全站联动"）
- **问题定性**：theme_cvd.apply 只改 CSS 变量（--ac 等），但按钮/导航/光斑/AI 钮大量直接写死 `rgba(229,71,109,…)` / `rgba(118,84,255,…)` / 十六进制渐变——变量改了它们不动，模拟演示"背景之外零变化"，评委看到的校色前后对比失效。
- **核心手法（相对色语法）**：CSS Color Level 5 `rgb(from var(--ac) r g b / α)`——所有透明度变体从单一 --ac 派生；theme_cvd 改一个变量，全站同色系跟随。样式/tryon/products/cvd/palette 共 **34 处 rgba → rgb(from …)**；tryon.css 按钮渐变/accent-color、products.css 时间线圆点、style.css :root 新增 `--vio:#7654ff;--org:#ff9650`（紫/橙装饰色入池）、**chatbox.js AI 悬浮钮内联渐变**也 var 化（内联样式可用 var()，各页都引了含 :root 的 style.css）。
- **theme_cvd.js 扩充**：VARS 增加 --vio/--org 两条（校色时同步变换）；新增 **URL 直达演示参数 `?cvdsim=deutan|protan|tritan`**（可叠加 `?cvdsev=0.5` 调严重度、`?cvdmode=correct` 看校色补偿态）——优先于档案加载，评委不用注册测色盲即可看"色盲眼中的世界"。
- **验证（headless 双截图对比）**：正常视角粉紫主色 vs `?cvdsim=deutan` 后——Logo 渐变/科普标题/轮播指示条/背景光斑/AI 钮全部变为绿盲眼中的土灰/暗蓝灰调；商品真实色与照片不受污染（只有品牌装饰色走变量）。esprima 全绿、版本号统一 bump def32。
- **边界诚实**：深紫黑底 #181220 在 protan/deutan 下数学 ΔE 个位数不可辨——模拟后"背景没变"部分是正常物理（Machado 矩阵对该色本来就几乎恒等），主因（硬编码前景色）已根治。

### def 33 ✅ 全站模拟入口做进第三部分（按钮组）+ 修复 URL 演示被档案恢复抹掉
- **问题定性（用户实测"刷新后没反应"暴露两个真 bug）**：① `?cvdsim=deutan` 的模拟先应用，但 cvd 页档案恢复路径对 uncertain 档案调 `applyTheme("correct","uncertain")` → theme_cvd 里 `M_FULL["uncertain"]` 不存在 → `resetTheme()` 把 URL 模拟刚设的 CSS 变量全部清除（headless 截图证实两视角完全同色）；② 页面加载 `renderProfile` 内的 `showTab("profile")` 异步执行，覆盖了 `#verify` 锚点直达——模拟还在但视觉上"什么都没发生"。
- **修复（演示优先锁）**：theme_cvd.js URL 参数分支置 `window.__cvd_url_sim = true`；cvd.js 档案恢复的 applyTheme 加 `!window.__cvd_url_sim` 门槛（URL 演示优先于档案恢复，用户显式的 doCalibrate 不受锁影响）；`showTab("profile")` 改为 `if(!location.hash)`（锚点直达优先）。calstatus 在 URL 接管时追加一行说明。
- **第三部分新增「全站模拟」按钮组**：绿色盲/红色盲/蓝黄盲/恢复原色四键——`simAll()` 薄封装 `CVDTheme.apply("simulate",…)`（与 URL 参数走同一 applyTheme，语义一致），severity 复用下方现有滑轨；选中态 `.simbtn.on` 与 `.cvd-tab.on` 同款相对色渐变（模拟下跟随变色，cvd.css 追加）。按钮组上方说明：临时演示不写入档案、刷新即恢复、长期生效走「档案与校色」。
- **锚点直达**：`cvd.html#verify` / `#profile` 直开对应 tab——评委演示/分享可一键直达第三部分，同时让 headless 截图可以拍到该面板。
- **验证（headless 双截图）**：`#verify` 直达第三部分、四按钮完整渲染；`?cvdsim=deutan#verify` 下全站（Logo/导航高亮/tab 选中态/按钮组/AI 钮/背景光斑）整体转为蓝灰土黄调且不再被档案恢复抹掉。Python esprima 校验全绿；全站 HTML 版本号统一 bump def33。
- **口径不变**：模拟 = 临时视觉演示，不写入档案、刷新即恢复；要长期生效仍在「档案与校色」保存校色模式（def 30 口径）。

### def 34 ✅ 校色启停与配置导入解耦：顶部开关 = 唯一启停，模式按钮 = 只导入配置

- **问题定性（用户 2026-09-21 定稿）**：档案页「校色模式/模拟模式/关闭」按钮既写档案又直接驱动全站配色，与顶部「校色配色」开关职责重叠冲突——按钮点了「模拟模式」全站立刻变色但开关仍显示关，两处状态源各说各话；试妆反解也只看 mode 不看开关。
- **数据模型**：calibration 新增 **`enabled` 启停位**——mode 变纯配置（correct/simulate/off = 导入了什么），enabled 决定是否生效（开关独占）。旧档案读档时 `_load_profile` 按 `mode!=off` 推导补默认（向后兼容）；`_save_profile` 落盘格式不变。
- **后端**：`calibrate(mode=None, enabled=None)` 双语义——传 `mode` = 纯导入（写 mode、enabled 保持现状，导入 ≠ 开启）；传 `enabled` = 启停切换（写 enabled、mode 不动；特例：mode=off 时开开关 → 自动升级 correct，保住 def 26「测评完点开关即开启」的唯一动作旅程）。`CalibrateIn` 显式 `Optional`（pydantic v2 不做 implicit optional 推断）。**试妆反解条件同步**：`mode=="correct" 且 enabled`（main.py），开关关 = 校色关闭，反解通道如实提示"开关未开"。
- **前端（cvd.js）**：`toggleCalSwitch` 只切 enabled；`doCalibrate(mode, enabled)` 双语义入口（按钮 POST {mode} / 开关 POST {enabled}）；新增 **`renderCalState` 统一渲染**——页面配色完全跟随 enabled（开 → `CVDTheme.apply(cal.mode,…)`，关 → reset），calstatus 三态文案（未导入配置 / 已导入·导入≠开启 / 已启用·可随时停用），uncertain 诚实说明与 def 33 URL 演示锁说明并入其中，renderProfile 恢复路径与按钮/开关回包共用同一函数（单一状态源，冲突根除）。theme_cvd.js 自动恢复条件同步加 `enabled!==false`。
- **验证**：状态机 7 用例直测全过（导入保启停 / 开关保配置 / off+开→升级 correct / 非法 mode 拒绝 / null 安全），HTTP 层四步冒烟全过后档案恢复原状；headless 双态实证——off 态截图（开关灰 + 「已导入配置…导入 ≠ 开启」）、on 态 dump-dom（`cal-switch on` + 「已启用…顶部开关可随时停用」+ uncertain 诚实边界）；Python esprima / py_compile 全绿；全站 HTML 版本统一 bump def34。
- **备注**：on 态 headless 截图里开关视觉停在 off 是虚拟时间下 CSS transition（left/background .25s）未推进的截图伪影，DOM class 与文案均已实证 on——实机点击动画正常。

### def 35 ✅ 校色配置缓存：关闭/重开不再丢配置（「关闭」= 只关启停）
- **问题定性（用户 2026-09-21 实测反馈）**：导入校色配置后点「关闭」再开开关，配置丢了——旧版「关闭」按钮把 mode 写成 off（清掉已导入的 correct/simulate 配置），再开开关时 off 状态触发 correct 兜底升级，用户导入的模式（如模拟模式）被 correct 静默覆盖。
- **修复（配置永久缓存）**：「关闭」按钮改为 `doCalibrate(null,false)` = 只关启停；后端 `calibrate` 的 mode=off 分支重写为**关闭动作**——`enabled=False` 且 mode 原样保留（API 层兼容：旧客户端发 off 也不再清配置）；mode=off 仅作为「从未导入过配置」的历史数据存在，此时开开关才走 correct 升级兜底。
- **def 26 旅程顺带修正**：测评完成自动导入从占位 `mode:"off"` 改为导入真实配置 `{mode:"correct"}` + `enabled=false`（导入 ≠ 开启口径不变）——calstatus「校色配置已根据档案自动导入」名副其实，点开关即生效。
- **验证**：状态机直测全过（核心链：导入 simulate → 关闭 → mode 仍 simulate/enabled=false → 再开 → simulate 完好恢复；旧数据 off+开 → correct 升级兜底保留）；HTTP 层完整复现用户操作序列 VERIFIED；esprima 全绿；全站 bump def35；测试后档案恢复用户快照（correct/enabled=false）。

### def 36 ✅ 全站配色统一出口：开关启停不再清空「全站模拟」演示态
- **问题定性（用户 2026-09-21 二次反馈）**：在色彩校验 tab 点「绿色盲」等全站模拟后，关/开顶部开关会把演示配色 reset 掉（按钮仍高亮但页面回原色，状态脱节）——renderCalState 的开关分支直接 apply/reset，不知道演示态存在；def 33 只给 URL 演示（?cvdsim）加了锁，按钮演示没有锁。
- **修复（applyColorState 统一出口）**：新增 `applyColorState()` 全站配色唯一出口——优先级 = URL 演示锁 > 演示态（`[data-sim].on` 按钮高亮即单一状态源，severity 取滑轨当前值）> 配置层（开关 on 且已导入 mode）> 原色 reset。renderCalState 改为缓存 `__cvd_cal_cache` + 调用它；simAll「恢复原色」也走它（退出演示 → 回配置层配色或原色，不再无脑 reset）。开关启停遇演示态 = 恢复演示色而非清空；calstatus 演示态追加说明「开关启停不会抹掉它，点恢复原色或刷新即回配置层配色」；uncertain 诚实文案仅非演示态显示。
- **验证**：esprima 全绿；headless 截图回归（#verify 直达正常渲染、加载路径无 JS 崩溃）；演示保持 / 恢复原色 / URL 锁三场景逻辑走查通过，待用户实测确认。

### def 37 ✅ 开关总控语义定稿：off = 全站立即原色（演示/配置暂停但状态保留）
- **问题定性（用户 2026-09-21 三次反馈）**：def 36 把演示态优先级抬到开关之上后，开关滑到左边（off）页面仍保留演示配色——违反「顶部开关控制全站校色配色」的总控语义。用户定稿口径：**off = 一切配色必须立刻停**（全站原色）；**on = 恢复配色**（有演示选择恢复演示，否则按配置层）；on↔off 反复切换不丢任何状态。
- **修复**：`applyColorState` 优先级链改为 URL 演示锁 > **开关总控（off → reset 短路）** > 演示态 > 配置层 > 原色；`renderCalState` 演示说明分两态（on=正在生效可开关启停 / off=已选中但暂停，重开即恢复）；`simAll` 开关关闭时点演示按钮只记录选择不上色（提示打开开关即生效），「恢复原色」文案分开关两态。
- **语义闭环**：绿色盲演示中 → 关开关（全站原色，按钮仍高亮=选择保留）→ 开开关（演示色恢复）→ 点「恢复原色」（退出演示，回配置层或原色）→ 刷新（一切按档恢复）。URL 演示锁（?cvdsim）不受开关控制保持 def 33 评委直达口径。
- **验证**：esprima 全绿；全站 bump def37；状态机走查（off 短路 / on 演示恢复 / 演示按钮 off 记录 / URL 锁不变）四场景通过。

### def 38 ✅ 全站渲染性能优化：清除无效 backdrop-filter（无硬件加速卡顿 / 开硬件加速抽风的根因）
- **问题定性（用户 2026-09-21）**：浏览器不开硬件加速页面卡、开了硬件加速浏览器整体抽风。排查结论：色盲模拟**不是**全页 SVG filter（theme_cvd.js 是一次性算好写 CSS 变量，性能友好）；真凶是全站十几个元素同时挂 `backdrop-filter:blur(16~20px) saturate(140~150%)`——每个元素要把身后内容渲染成纹理再做高斯卷积：软件渲染下 CPU 光栅化跑满（卡），GPU 模式下大面积模糊纹理叠加压垮合成器（核显驱动抽风）。**关键判断：这些毛玻璃背后全是静态渐变背景，模糊渐变在视觉上零收益**——纯浪费。
- **清除清单**：style.css `.card`/`.flow`/`button`（全站按钮!）/`.science`；cvd.css `.cvd-content`；chatbox.js `#cb-panel`（92% 底色 + blur20px）；palette.html `.ujpanel`（96% 底色）/`#unifs`/`#cmpfs`（92% 底色）；products.css `.pd-overlay`。补偿策略：半透明底色不透明度小幅上调（.055→.07、.82→.88、overlay .74→.85），玻璃拟态观感不变；`#cb-panel.no-anim` 显式关闭类保留。
- **顺带**：cvd.css `.cvd-tab` 的 `transition:all` 收窄为 color/border-color/background 三属性（避免全属性过渡监听）。
- **验证**：残留扫描干净（仅剩注释与显式关闭类）；chatbox.js esprima 全绿；全站 bump def38；headless 截图视觉回归（观感与改前无差异）。


### def 39（2026-09-21）· 全站校色开关注入 + uncertain 边界解释（用户反馈：切页后开关消失、校色不保留）
- **诊断**：①「校色开关消失」= 开关 DOM 只存在于 cvd.html 头部，选色/试妆/产品库/主页四页 site-head 里根本没有（功能缺口非 bug）；②「校色不保留」= 用户档案 kind=uncertain + enabled=true，theme_cvd.js 跨页恢复时 uncertain 不在 Machado 矩阵表（数学边界：类型未定不做定向补偿），页面保持原色，且其他页面无 calstatus 提示区 → 用户感知为校色丢失。
- **修复（新增 `calswitch.js` 全站开关组件）**：在无 `.cal-switch` 的 site-head 页面自动注入「校色配色」开关（插在导航前）；fetch profile 同步开关态（on/off 跟随 calibration.enabled）；点击 POST `/api/cvd/exam/calibrate` {enabled} 后立即调 `CVDTheme.apply/reset` 页面即时变色，语义与 cvd 页完全一致（def 34 开关=唯一启停）；URL 演示锁页面（?cvdsim）切换只写档案不动演示配色；无档案点击 → toast 提示先测评。cvd.html 有原生开关（含 calstatus），组件检测到即退出不重复注入。
- **uncertain 诚实边界提示**：theme_cvd.js 暴露 `CVDTheme.hasKind(k)`（单一真相源）；组件在「开关 on 但 kind 不在矩阵表」时 toast 说明「未定型类型按保守口径不做页面颜色补偿、试妆反解照常」，初始加载每会话提示一次（sessionStorage 去重），toggle 时即时反馈。
- **样式上移**：`.cal-switch/.cal-track/.cal-knob/.cal-label` 从 cvd.css 移植到 style.css 末尾（全站共享），cvd.html 静态开关同用一组 class，零圆角锚点不变。
- **验证**：calswitch.js + theme_cvd.js esprima 全绿；headless 截图产品库页开关渲染成功且 on 态与档案一致；dump-dom 确认 cvd 页原生开关不受影响（cal-switch on + data-has-profile=1）；全站 bump **def39**。

### def 40（2026-09-21）· uncertain 档案全站中性增强（用户反馈：切到试妆/主页/产品库/选色「没有对应的修正」）
- **根因**：def 39 只解决了「开关跨页消失」，但用户档案 kind=uncertain 不在 Machado 矩阵表 → theme_cvd.js 的 IIFE 自动恢复条件 `M_FULL[cal.kind]` 直接跳过 + applyTheme 返回 kind_unsupported → **所有页面都不上色**，诚实边界在用户视角等价于「校色失效」。
- **数学（新增 uncertain 中性增强矩阵，与 Machado 同域：线性 RGB + severity 插值 (1−s)I+sM）**：
  `M_UNC = [[1.45,-0.45,0],[-0.1338,1.1338,0],[0,0,1]]`——R'=R+0.45(R−G)，G'=G+0.2973·0.45·(G−R)，系数比取 Y 加权（0.2126:0.7152）→ **亮度严格恒定**；红绿色差线性域放大约 1.58 倍（sev=0.6 插值后 1.35×）；黄轴（R=G）不动、纯红/纯绿差为零色零变化、蓝紫轴不动。**方向无关**：不假定红弱/绿弱，双向拉开红绿轴，deutan/protan 都受益且不会补错方向。
- **实现**：theme_cvd.js `M_FULL.uncertain = M_UNC`（matFor/hasKind/URL ?cvdsim=uncertain 自动获得能力）；`transformRGB` 对 uncertain 走**正向增强**（绕开 correct 的残差补偿 `2I−M`——对增强矩阵反推会反向缩小色差，必须绕开）；IIFE 自动恢复条件 `M_FULL[cal.kind]` 现在对 uncertain 成立 → **主页/选色/试妆/产品库/cvd 全站自动上色**，无需改各页。
- **文案三处同步**：cvd.js renderCalState 新增 uncertain 生效说明（「对称红绿增强…重测出明确类型后校色会更精准」，截图已验证上屏）；calswitch.js toggle toast 按 kind=uncertain 给增强说明；初始加载的「不做补偿」提示对 uncertain 不再触发（hasKind 现为 true）。
- **数值验证（Python 同公式复算）**：主色 #e5476d → #fd106d（R−G 0.715→0.966，恰 1.35×）；ΔY=0.0009（亮度恒定）；纯红/黄零变化 ✓；高亮红（ac2/org）有 ~4% Y 损失属色域截断（Machado 同样存在），视觉为「更艳」非失真。
- **验证**：theme_cvd.js + cvd.js + calswitch.js esprima 全绿；试妆页截图全站粉调增强可见；cvd 页 #profile 直达截图 calstatus 增强说明上屏；dump-dom 确认开关 on + body inline background（applyTheme 已执行）；全站 bump **def40**（15 处引用）。headless 截图偶发开关 knob 呈 off 视觉为虚拟时间冻结 CSS transition 的假象，以 dump-dom class 为准。

### def 41（2026-09-21）· 配色纯会话手动模式（用户反馈：①选绿盲模拟切页「变成黄色盲」②要求默认进入 = 无色盲，点了才模拟）
- **根因**：def 40 让档案 calibration 自动驱动全站配色后，用户在 cvd 页点的绿盲演示（`[data-sim].on` 仅本页 DOM 态，不跨页）切页即丢，theme_cvd.js IIFE 又自动恢复档案的 uncertain 增强——用户点了 A 生效的是 B，感知为「变成另一种色盲」。设计层矛盾：档案 enabled 自动上色 ≠ 用户「默认原色」预期。
- **新口径（用户 2026-09-21 定稿）**：**配色 = 纯会话手动模式**。唯一真相源 = `sessionStorage.cvd_theme`（JSON `{mode,kind,sev}`）：新会话/无标记 = 原色（默认无色盲）；用户主动操作（开关 on / 模拟卡片 / 恢复原色）才写标记，跨页/刷新一致恢复；关开关/关浏览器 = 清标记回原色。**档案 calibration 退役为后端管线专用**（试妆反解、守门、AI 工具照常消费），不再驱动页面配色；`enabled` 字段保留存档但前端不读。
- **实现**：theme_cvd.js 新增 `getSession/setSession` 并入 `window.CVDTheme` 导出；IIFE 删除档案 fetch 自动恢复，改读会话标记（`?cvdsim` URL 锁保持最高优先级、不写标记）。calswitch.js `isOn()`=会话标记（开关初始态同步可读、新会话默认 off）、toggle 本地先写标记再 POST 存档（失败/异常回滚 prev）、初始化 render() 提前不依赖 fetch。cvd.js：`renderCalState` 的 on=!!sess；`applyColorState` 优先级=URL 锁 > 开关 off > 会话标记 > 演示 DOM > 配置层 > 原色；`toggleCalSwitch`/`simAll` 本地先写标记（演示选中时开启开关=演示生效，保留 def 37 口径）；`doCalibrate(mode)` 导入路径在开关 on 且非演示态时同步标记；「刷新即恢复」等文案改为「跨页保留（本会话内）」。
- **一致性要点**：标记写入点收敛为 toggle/simAll/doCalibrate(mode) 三处（本地先行），renderCalState 只读不写，避免「初始进页读档案时误覆盖演示标记」；URL 演示锁下所有写入被挡，评委演示不污染用户会话。
- **验证**：三文件 esprima 全绿；headless 全新会话主页 = **原色 + 开关 off**（body 无 inline style，对照 def40 截图的艳粉增强）；`?cvdsim=deutan` URL 锁截图 = 全站绿盲模拟生效且开关 off（不污染标记）；全站 bump **def41**（15 处引用）。

### def 42（2026-09-21）· 色盘与照片的同源矩阵滤镜（用户反馈：校色没有覆盖到色盘和上传的照片，要求蒙一层滤镜）
- **根因**：applyTheme 只重写 CSS 变量（--ac 等）+ body 背景——canvas 像素（选色页全域色盘 `#uniwall`，256 层 RGB 渐变 + 商品色框标记全在 canvas 内）与照片 `<img>`（试妆上传预览 `#upzone img`、结果图 `.imgbox img`，均为动态 innerHTML 插入）不吃 CSS 变量，校色/模拟对这些内容无效。
- **方案（SVG feColorMatrix 滤镜，用户口径「蒙一层滤镜」的数学精确版）**：theme_cvd.js 新增 `mediaMatrix(mode,kind,sev)` 把三种语义归一为线性域 3x3——simulate/uncertain → (1−s)I + sM（正向）；correct → (1+s)I − sM（残差补偿 2I − M_sev 的展开，同为线性矩阵）——注入 `<filter id="cvdmat" color-interpolation-filters="linearRGB"><feColorMatrix>`（浏览器自动 sRGB↔linear 解码/编码后在线性域乘矩阵，**与 transformRGB/Machado 严格同域**，GPU 加速零逐像素成本），给匹配元素挂 `style.filter=url(#cvdmat)`；alpha 行恒等（照片透明度不受影响）。
- **动态覆盖**：MutationObserver 监听 body 子树新增节点，命中 `#uniwall / #upzone img / .imgbox img` 自动挂滤镜（试妆照片是后插入的）；applyTheme 成功时对现有匹配元素 paintMedia；resetTheme 摘除全部滤镜。色盘全屏 = 同一 canvas 搬家（appendChild），filter 跨全屏保留。
- **刻意不蒙**：石原测评图（测评刺激，蒙了改变结果=作弊）、cvd 页 verify 的模拟预览图（本身已是模拟输出，二次模拟会失真）——均不在 MEDIA_SEL。
- **验证**：三文件 esprima 全绿；dump-dom 确认 svg filter 注入 + #uniwall 挂 filter；截图对照——原色色盘红绿蓝黄全谱鲜艳 vs `?cvdsim=deutan` 色盘红绿轴塌向黄蓝（商品色框同步变换，与页面 CSS 变量路径模拟一致）；试妆页 filter 注入无副作用；全站 bump **def42**（15 处引用）。

### def 43（2026-09-22）· 上传即人脸解析 → 五官档案 → AI 一键配妆（用户反馈：用 PyTorch 做部位分析后自动提取肤色/头发/眉毛等描述填入 AI，其他交给 AI 推荐，省 token 提效率；照片先做色校正保证识别准确）
- **定位**：tryon.html L245 的 def 16 预留位（「上传即分析 → 自动肤色 → 精确色号回填表单」）落地。链路：上传/恢复照片 → 自动 `POST /api/face_profile` → 白平衡校正 + BiSeNet 解析 → 分部位取色 → 前端档案面板 → 一键把检测事实注入 AI 对话 → AI 调 recommend_shade_tool → 既有 fill 通路回填五张部位卡。
- **算法层（beauty/face_profile.py，新模块，不依赖 torch——BiSeNet 由服务层传入）**：
  - 白平衡：Gray-World 温和版（gain 限幅 [0.80,1.25] + 0.65 混合，防过校正）；
  - **双版本取色择优（色偏对策核心）**：原图/校正图各自在 skin mask 统计中值色，按 YCbCr 经验肤色域（Cb∈[77,127] Cr∈[133,177]）算偏离分，分低者胜——机制性防「白皮拍成黄皮」也防「越校越黄」；肤色域总分 >9 注记「浓妆/滤镜脸，仅供参考」；
  - 取色卫生：各类 mask 先 erode 去边缘混色像素，中值色抗高光；虹膜只取眼裂中心小椭圆（eye 类含眼白），剔除眼白高光；
  - 分类口径：肤色 = ITA°（Chardon 六档：极白皙/白皙/自然/小麦/浅棕/深棕）+ a*/(a*+b*) 冷暖底调；发眉瞳唇 = L* 分档 + b*−a* 金调 / a* 红调条件；脸型 = skin 类宽高比三档 + 下颌宽比（CelebAMask skin 不含脖颈，标「粗略估计」）；
  - 质量降级不瞒报：mask 面积比 < _MIN_RATIO → status=unknown（前端灰显、AI 消息如实带出）；检测到眼镜类(6) → 瞳色注记「仅供参考」。
- **服务层**：tryon_service.run_face_profile（复用 _get_net 单例，与试妆共用一次模型加载）+ main.py `POST /api/face_profile`（10MB 上限、run_in_threadpool 防阻塞）。
- **AI 集成（省 token 关键）**：fpRecommend() 组装一条结构化事实消息（肤色 hex+档位+底调 / 发/眉/瞳/唇 hex+名称 / 脸型；unknown 写「未检出，按常规推荐」）经 CBChat.send 进对话——**AI 不看图、不反问外貌**，直接调 recommend_shade_tool 一次出全 5 部位；prompt.py recommend_shade_tool 描述同步加「人脸档案=事实，禁止反问外貌；未检出部位按肤色给常规安全色」。对比用户手打外貌描述：省输入、省澄清轮次，推荐还更准。
- **前端**：tryon.html 面板（cpanel 风格，ty-left 尾部）；tryon.js analyzeFace（tyProfSeq 序号防连换照片竞态）+ renderFaceProf（unknown 灰显、correction.chosen=original 时显示「校正反而引入偏差，已按原图取色」）+ fpRecommend；tryon.css fp-row/fp-ai 样式。
- **验证**：
  - 算法单测（scripts/testing_scripts/test_face_profile.py，保留）：白平衡合成图校正后均值 201.3（目标 200）、gains 方向正确；11053.jpg 端到端五项全检出（肤 #B77B68 小麦·冷调 / 发 #0B0A0C 黑 / 眉 #6B554E 深棕 / 瞳 #42373D 棕（虹膜提取成功）/ 唇 #B66C71 红润 / 脸型椭圆 1.35）；
  - **偏色鲁棒**：人造整体偏黄图（×[0.90,0.98,1.14]）→ 机制自动选 white_balanced 版，肤色距基准仅 RGB 5.8、档位一致（小麦）——「白皮拍成黄皮」对策实测有效；
  - HTTP 冒烟：/api/face_profile ok=True device=cuda，档案与本地一致；
  - **CDP headless 全链路（真实 AI）**：DataTransfer 注入真实照片派发 change → 面板 7 行渲染 5/5 识别 → fpRecommend → AI 回复「收到，检测数据已采信」并并行调 get_vision_profile_tool + foundation_search_tool → recommend_shade_tool 5 部位 → **fill 回填全部生效**（lip #A63D57 莓果玫红 / foundation #C27F48 集团库真实色 / eyeshadow #9B7B7D 灰玫瑰 / brow #59453E 贴近原生深棕 / blush #C9808C），推荐话术完全基于检测事实（「冷调小麦肌的玫瑰系同族配色…眉贴近原生深棕」）；截图确认面板与回填；
  - 修复两处：face_shape 尾部截断返回 null（补 ratio 判定+return）；面板复用 .cpanel 基类默认 opacity:0 需挂 .show（截图对照发现）。
  - tryon.js esprima 绿（python-esprima 不支持 ES2020 可选链，既有 2 处 `?.` 替换后 parse 验证；新增段未用）；python 4 文件 ast 全绿；全站 bump **def43**（tryon.js 独立版本号 def31→def43 同步）。
  - 已知边界：eye 阈值放宽至 0.002（11053 眼裂 0.0036 曾误判 unknown）；测试用临时截图/CDP 脚本已清理，仅留 test_face_profile.py。


### def 44（2026-09-22）· 大模型接入彻底外置 + 本地大模型一等公民（用户：models 指大模型 API/本地大模型，不是权重文件夹；要一个外部配置文件方便替换填写）
- **痛点**：def 7 起 base_url/api_key/model 已在 secrets.local.json 外置，但 ① 文件名不表意、藏在 backend 深处；② 本地大模型（llama.cpp/ollama）无预设且 api_key 强制必填——本地服务无鉴权会被校验拦死；③ 新增 provider 需理解 _DEFAULTS 深合并细节。
- **实现**：新增 `app/backend/llm.local.json`（唯一生效文件，现网 key 自 secrets.local.json 平移，provider=zhipu 无感切换）+ `llm.local.example.json`（模板入库，`_说明/_填写步骤/_换本地大模型` 文档字段——config 合并时跳过 `_` 前缀键，沿用既有惯例）。config.py：`_resolve_config_path` 优先级 llm.local.json > secrets.local.json（兼容读，旧文件退役仅作回滚备份）> 缺失时报错引导复制模板；`_DEFAULTS` 增 llamacpp（127.0.0.1:8080/v1/chat/completions）/ollama（11434）本地预设；校验放宽——urlparse 取 host，本地（127.0.0.1/localhost/::1）api_key 允许留空，云端仍 fail fast；新增 model 非空校验（报错点名文件与填写示例）。llm_client.py 两处 headers 改条件构造：api_key 空则不发 Authorization 头。agent_loop.py `_LEAK_PATTERNS` 出口护栏补 `llm\.local`。.gitignore 加 `llm.local.json`；README 补「大模型接入」章节。
- **特性**：每次对话重读配置 → 改 llm.local.json 即时生效（换 provider 不用重启）；本地/云端同 OpenAI 兼容协议零代码切换。
- **顺带修复（服务端变更追平）**：智谱 glm-5.3-flash 已改"始终思考"——`thinking:{"type":"disabled"}` 与 `{"type":"low"}` 均被拒（HTTP 400 code 1210，实测 2026-09-22；def 22/29 的 disabled 提速姿势失效）；探测确认**不发送 thinking 字段 = 200**。zhipu 默认 thinking 置 null（llm_client 对 None 本就不发送）；代价 = 思维链必产（reasoning_content 已剥离不上屏，流式 ping 心跳防看门狗误杀）、非流式 max_tokens 必须给足（def 8 注释的坑重新生效）。
- **验证**：ast 三文件绿；`_resolve_config_path` 选中新文件、load_secrets 读出 zhipu/glm-5.3-flash/key 掩码非空；example 模板（云端空 key）触发引导话术；临时 ollama 空 key 配置通过校验；真实 llm_chat 冒烟 200、content="OK"、_error=None、usage.reasoning_tokens=76（思维链剥离生效）。


### def 45（2026-09-22）· 大模型接入改环境变量（用户：key 写在文件里会有泄露和 api 盗用风险，全部改成初始化时从环境读取）
- **动机**：def 44 的 llm.local.json 虽被 gitignore，但 key 仍以明文存在于"随项目走"的文件里——误提交/打压缩包分享即泄露。用户要求接入信息全部从初始化环境读取，仓库内零明文。
- **实现**：新增 `app/backend/.env`（唯一秘密载体，.gitignore 的 `.env` 规则已覆盖；现网双 key 平移后 **llm.local.json / secrets.local.json / llm.local.example.json 三文件删除**）+ `.env.example`（全注释模板入库）。config.py 重写：`_load_dotenv` 手写最小解析（KEY=VALUE / # 注释 / 去引号；真实环境变量优先、不覆盖已有；零第三方依赖，import config 时自动加载）；变量协议 `LLM_PROVIDER` + `LLM_<名字>_API_KEY/_BASE_URL/_MODEL`（provider 集合 = 内置预设 ∪ 从 env 变量名反推，自定义引擎加变量即生效）；`_PRESETS` 只存非敏感 base_url/model/thinking——**代码与入库文件零 key**；校验同 def 44（云端 key 必填 fail fast、本地 127.0.0.1 放行、model 必填），报错话术全部指向 .env。agent_loop.py `_LEAK_PATTERNS` 出口护栏升级：`\.env`、`llm_*api_key` 变量名、智谱 key 形态 `[0-9a-f]{32}\.[0-9a-z]{8,}`（prompt 注入诱导吐 key 的兜底）。gitignore 移除 llm.local.json 行；README「大模型接入」章节改写为 .env 版。
- **特性**：打包/分享项目零处理即安全（.env 不在仓库）；部署平台直接配环境变量优先于 .env（12-factor）；改 .env 即时生效（每次对话重读环境）。
- **验证**：ast 三文件绿；.env 自动加载（LLM_PROVIDER=zhipu 注入 os.environ）；四引擎组装 + key 掩码非空；临时 ollama 空 key 通过校验；云端空 key 触发引导话术；真实 llm_chat 冒烟 200、content="OK"（key 全程走 .env→env 链路）；git status 中 .env 隐形、.env.example 正常入库。

