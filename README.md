# ColorBoundless · 色无界限

> 基于多模态 Agent 与视觉感知重构的包容性美妆无障碍系统
> 2026 欧莱雅美妆科技黑客松 · 赛题3「无界体验家」

**一句话**：让色觉异常用户也能「看见」彩妆——色觉测评 → 色号精准推荐 → AI 试妆 → 对话式搭配建议的完整闭环，人脸数据全程不出本机。

## 核心能力

| 模块 | 状态 | 技术 | 验证指标 |
|---|---|---|---|
| 色觉测评（CVD Screening） | ✅ | 石原板/色相排列/网格测试 + 规则状态机分诊 | triage 全绿（test_triage.py） |
| 色号精准推荐 | ✅ | CIEDE2000 色差算法 · CIELab 空间排序 | 正红匹配 ΔLab = 1.1 |
| AI 虚拟试妆 | ✅ | BiSeNet 人脸解析 + Lab 颜色迁移 + 羽化 | 纯 CPU 0.17s/图（实测） |
| 双 Agent 对话 | 🔨 进行中 | LangChain 1.x create_agent + LangGraph 工具循环 | — |
| 检索索引（4 库） | ✅ | 262K 色 KMeans 聚类 + undertone 查询表 + 风格 RAG | 检索 0.1~0.2s |
| 波浪图可视化 | 🔨 进行中 | 光谱波动模拟（spectrum_wave_demo.py） | — |

## 架构

```
数据层          算法层                 Agent 层              应用层
data/    →     cvd_test/   ──┐                              ┌─ FastAPI
4 类索引        beauty/     ──┼── agents/（LangGraph） ──→  └─ Gradio
              models/       ──┘   工具化调用算法层              (9/6 起开发)
```

**设计原则**：LLM 自由度显式约束在「语言层」，数字与决策全部下沉算法层（CIEDE2000 / 规则状态机）——可解释、可复现、防幻觉。

## 快速开始

```bash
git clone https://github.com/xianyubingyuhuo/ColorBoundless.git && cd ColorBoundless
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
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

## 目录结构

```text
ColorBoundless/
├── app/          # 前后端应用（FastAPI + Gradio，开发中）
├── agents/       # 双 Agent 层：测评诊断 / 美学顾问（开发中）
├── beauty/       # 试妆能力：lipstick ✅ eyebrow ✅ eyeshadow ⬜ foundation ⬜
├── cvd_test/     # 色觉测评：ishihara / hue / grid + triage 状态机 ✅
├── cv/           # 图像与色彩算法层
├── data/         # 数据层：raw → processed → knowledge_base → 索引
├── models/       # 权重（不入库）与检索索引（4 个 .npz 已入库）
├── scripts/      # 一次性数据工厂 + 测试脚本（test_* / diag_*）
├── results/      # 输出（git 忽略）
└── docs/         # 设计文档（DESIGN.md：数据落库与配色体系设计）
```

## 技术决策（答辩要点）

- **色号检索为什么不用向量？** 色号库是结构化色彩数据，CIEDE2000 精确排序比向量检索更准更快——可复算、可解释。
- **分诊为什么用规则状态机不用 LLM 编排？** 测评环节要求可解释、可复现、零幻觉；LLM 被约束在语言层做「翻译」。
- **为什么保留本地推理模式？** 人脸是敏感数据：云端版照片不出服务器，离线版照片不出本机，大模型只接收 Lab 值/档位/色号等结构化数字。

## 路线图（2026-09-30 交卷）

- [x] 色觉测评三件套 + 分诊状态机
- [x] 试妆引擎（唇/眉）+ 色号库 + 四索引
- [ ] FastAPI + Gradio 应用壳（9/6-9/11）
- [ ] Agent 层落地（9/12-9/17）
- [ ] 试妆间 + 波浪图页（9/18-9/24）
- [ ] 演示视频 + 部署 + 交卷（9/25-9/30）

## 许可证与数据来源

- CelebAMask-HQ 权重：仅限非商业研究/教育用途
- face-parsing.PyTorch：MIT
- 品牌色号与趋势图像资源遵循对应版权要求；完整设计思路见 [docs/DESIGN.md](docs/DESIGN.md)
