# -*- coding: utf-8 -*-
"""def 9 · FastAPI 骨架：三件工具的 HTTP 测试端点 + /api/chat 直通 + 前端静态页。

一键启动（项目根执行）：
    .venv/Scripts/python.exe app/backend/main.py
浏览器打开 http://127.0.0.1:8000/

路径纪律（复用 cwd 实验#2 结论）：本文件是唯一入口，ROOT = parents[2]
算出项目根插入 sys.path——无论从哪个目录启动，agents.tools.* 都能导入。
"""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))          # agents.tools.* 的导入链

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.tools.search_shade import search_shade_tool
from agents.tools.kb_search import kb_search_tool
from agents.tools.palette_search import palette_search_tool
from agent_loop import agent_reply      # def 11 · 大脑循环（function calling）
from tryon_service import run_tryon     # def 12a · 试妆（torch 全延迟导入，本模块级只拉 cv2/numpy）
from cvd_service import check_pair, preview_hex   # def 14 · 色盲视角（纯 numpy，零重依赖）


@asynccontextmanager
async def lifespan(_app):
    # kb 向量模型预热：不预热则首次提问要干等 62s（模型加载），预热后毫秒级。
    # 同步阻塞启动最简单可靠（lru_cache 单例没有并发竞态）。
    print("[lifespan] 预热 kb 向量模型（首次约 60s，仅启动时一次）...")
    kb_search_tool("预热", 1)
    print("[lifespan] 预热完成")
    yield


app = FastAPI(title="ColorBoundless 工具测试台", lifespan=lifespan)


class ChatIn(BaseModel):
    message: str


@app.get("/api/tools/search_shade")
def api_search_shade(hex: str, top_k: int = 5):
    """工具①：色号 → 最近官方色号"""
    return search_shade_tool(hex, top_k)


@app.get("/api/tools/kb_search")
def api_kb_search(query: str, top_k: int = 5):
    """工具②：知识库语义检索"""
    return kb_search_tool(query, top_k)


@app.get("/api/tools/palette_search")
def api_palette_search(hex: str, hue_group: str = None, top_k: int = 5):
    """工具③：全库色板粗排+精排"""
    return palette_search_tool(hex, hue_group=hue_group, top_k=top_k)


@app.post("/api/chat")
def api_chat(body: ChatIn):
    """def 11 · 大脑循环版：自动选工具 → 代码执行 → 结果喂回 → 正文"""
    return agent_reply(body.message)


MAX_IMG_BYTES = 10 * 1024 * 1024


@app.post("/api/tryon")
async def api_tryon(file: UploadFile = File(...), hex_color: str = Form(...),
                    alpha: float = Form(0.75)):
    """def 12b · 试妆：multipart 照片 + 色号 + 强度 → 原图/上妆图 base64（五件套 JSON）"""
    data = await file.read()
    if not data:
        return {"ok": False, "tool": "tryon", "error": "未收到图片数据", "results": {}}
    if len(data) > MAX_IMG_BYTES:
        return {"ok": False, "tool": "tryon", "error": "图片超过 10MB 限制", "results": {}}
    # 线程池跑同步推理：冷启动约 30s（torch 全链+权重）也不卡 event loop，/api/chat 照常响应
    return await run_in_threadpool(run_tryon, data, hex_color, alpha)


@app.get("/api/cvd/preview")
def api_cvd_preview(hex: str, cvd_type: str = "deuteranopia", severity: float = 1.0):
    """def 14 · 色盲视角预览：该色号在指定色觉缺陷用户眼中的等效颜色"""
    return preview_hex(hex, cvd_type, severity)


@app.get("/api/cvd/check")
def api_cvd_check(hex_a: str, hex_b: str, cvd_type: str = "deuteranopia"):
    """def 14 · 色对校验：正常 ΔE vs 模拟 ΔE + 规则库命中（avoid/safe）"""
    return check_pair(hex_a, hex_b, cvd_type)


# 前端静态页挂在 "/"，必须放在 API 路由之后定义（先注册的先匹配）
_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(_FRONTEND), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
