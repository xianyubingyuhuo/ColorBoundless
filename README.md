# ColorBoundless · 色无界限

> 基于多模态 Agent 与视觉感知重构的包容性美妆无障碍系统
> 2026 欧莱雅美妆科技黑客松 · 赛题3「无界体验家」

**一句话**：让色觉异常用户也能「看见」彩妆——色觉测评 → 色号精准推荐 → AI 试妆 → 对话式搭配建议的完整闭环，人脸数据全程不出本机。

## 核心能力

| 模块 | 状态 | 技术 | 验证指标 |
|---|---|---|---|
| 色觉测评（CVD Screening） | [OK] | 石原板/色相排列/网格测试 + 规则状态机分诊 | triage 全绿（test_triage.py） |
| 色号精准推荐 | [OK] | CIEDE2000 色差算法 · CIELab 空间排序 | 正红匹配 ΔLab = 1.1 |
| AI 虚拟试妆 | [OK] | BiSeNet 人脸解析 + Lab 颜色迁移 + 羽化 | 纯 CPU 0.17s/图（实测） |
| 双 Agent 对话 | [进行中] 进行中 | LangChain 1.x create_agent + LangGraph 工具循环 | — |
| 检索索引（4 库） | [OK] | 262K 色 KMeans 聚类 + undertone 查询表 + 风格 RAG | 检索 0.1~0.2s |
| 波浪图可视化 | [进行中] 进行中 | 光谱波动模拟（spectrum_wave_demo.py） | — |

## 架构

```
数据层 算法层 Agent 层 应用层
data/ → cvd_test/ ──┐ ┌─ FastAPI
4 类索引 beauty/ ──┼── agents/（LangGraph） ──→ └─ Gradio
              models/ ──┘ 工具化调用算法层 (9/6 起开发)
```

**设计原则**：LLM 自由度显式约束在「语言层」，数字与决策全部下沉算法层（CIEDE2000 / 规则状态机）——可解释、可复现、防幻觉。

## 快速开始

```bash
git clone https://github.com/xianyubingyuhuo/ColorBoundless.git && cd ColorBoundless
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
```

启动（一键，含向量模型预热约 60s）：

```powershell
.\start_system.ps1        # -NoBrowser 不自动开浏览器；-Stop 停止
```

```python
# 1. 色号检索（CIEDE2000）
from beauty.lipstick.shade_library import search_shade
chosen = search_shade("FF4D6D", top_k=1)[0]

# 2. AI 试妆（CPU 即可）
from beauty.lipstick.tryon import tryon
tryon("data/faces/11053.jpg", color=chosen["hex"])
```

## 模型权重

`models/face_parsing/79999_iter.pth`（50.8MB）不入库，从
[face-parsing.PyTorch](https://github.com/zllrunning/face-parsing.PyTorch) 获取后放入该目录。
检索索引（`models/vector_store/*.npz`）为自建资产，已入库，克隆即用。

## 大模型接入（LLM "大脑"）

密钥与地址全部走**环境变量**（def 45：代码与仓库文件里零明文 key，防泄露/盗用）：
复制 `app/backend/.env.example` 为同目录 `.env`（.gitignore 已排除，永不入库），
按注释填 `LLM_PROVIDER` 与 `LLM_<名字>_API_KEY`；部署平台也可直接配环境变量
（真实环境变量优先级高于 .env）。云端（DeepSeek / 智谱 GLM 等 OpenAI 兼容 API）
填 key；本地大模型选 `llamacpp`（默认 `http://127.0.0.1:8080/v1/chat/completions`）
或 `ollama`（`http://127.0.0.1:11434/v1/chat/completions`），填 `LLM_<名字>_MODEL`、
key 留空即可（本地服务无鉴权）。每次对话重读环境，改完 `.env` 即时生效。
**打包/分享项目时无需任何处理——.env 本就不在仓库里；如 key 曾在其他渠道泄露过，
建议去服务商控制台轮换。**

## 目录结构

```text
ColorBoundless/
├── app/ # 前后端应用（FastAPI + Gradio，开发中）
├── agents/ # 双 Agent 层：测评诊断 / 美学顾问（开发中）
├── beauty/ # 试妆能力：lipstick [OK] eyebrow [OK] eyeshadow [待办] foundation [待办]
├── cvd_test/ # 色觉测评：ishihara / hue / grid + triage 状态机 [OK]
├── cv/ # 图像与色彩算法层
├── data/ # 数据层：raw → processed → knowledge_base → 索引
├── models/ # 权重（不入库）与检索索引（4 个 .npz 已入库）
├── scripts/ # 一次性数据工厂 + 测试脚本（test_* / diag_*）
├── results/ # 输出（git 忽略）
└── docs/ # 设计文档（DESIGN.md：数据落库与配色体系设计）
```

## 演示清单（现场操作）

- **启动**：`.\start_system.ps1`（约 60s 模型预热），浏览器自动打开主页。
- **全新演示态保障**：F5 刷新、直接打开新标签、后端重启都会自动清空本地缓存
  （对话会话 / 校色状态 / 试妆照片槽）；小标签内跳转（顶部导航、AI 回填跳转）
  保留会话状态；后端重启后打开着的页面 4s 内自动感知并归零。
- **主线动线**：试妆页（上传照片 → AI 试妆 → 社会视角守门）→ AI 悬浮窗对话
  （色号问答，可一键回填试妆）→ 选色页（色号检索 → GB/T 命名 → 定制申请时间线）
  → 色盲校验页（22 题测评 → 档案 → 校色 / 全站模拟）。
- **校色语义**：未测评时打开「校色配色」= 对称红绿增强临时口径（可随时开关，
  「恢复原色」= 真原色）；完成测评后自动升级为个性化校色/模拟。
- **评委彩蛋**：`tryon.html?cvdsim=deutan` 直达绿色盲视角全站模拟，
  `&cvdsev=0.5` 调严重度，`&cvdmode=correct` 看校色补偿态。

## 技术决策（答辩要点）

- **色号检索为什么不用向量？** 色号库是结构化色彩数据，CIEDE2000 精确排序比向量检索更准更快——可复算、可解释。
- **分诊为什么用规则状态机不用 LLM 编排？** 测评环节要求可解释、可复现、零幻觉；LLM 被约束在语言层做「翻译」。
- **为什么保留本地推理模式？** 人脸是敏感数据：云端版照片不出服务器，离线版照片不出本机，大模型只接收 Lab 值/档位/色号等结构化数字。

## 路线图（2026-09-30 交卷）

- [x] 色觉测评三件套 + 分诊状态机
- [x] 试妆引擎（唇/眉）+ 色号库 + 四索引
- [x] FastAPI 应用壳（9/6-9/11，自研前端替代 Gradio）
- [x] Agent 层落地（9/12-9/17）
- [x] 试妆间 + 波浪图页（9/18-9/24）
- [ ] 演示视频 + 部署 + 交卷（9/25-9/30）

## 许可证与数据来源

- CelebAMask-HQ 权重：仅限非商业研究/教育用途
- face-parsing.PyTorch：MIT
- 品牌色号与趋势图像资源遵循对应版权要求；完整设计思路见 [docs/DESIGN.md](docs/DESIGN.md)
