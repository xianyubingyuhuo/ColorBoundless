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

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.tools.search_shade import search_shade_tool
from agents.tools.kb_search import kb_search_tool
from agents.tools.palette_search import palette_search_tool
from llm_client import llm_chat


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
    """大脑直通版（def 10 换成 function calling 工具循环）"""
    return llm_chat([{"role": "user", "content": body.message}])


# 前端静态页挂在 "/"，必须放在 API 路由之后定义（先注册的先匹配）
_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(_FRONTEND), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
