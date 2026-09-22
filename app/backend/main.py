# -*- coding: utf-8 -*-
"""def 9 · FastAPI 骨架：三件工具的 HTTP 测试端点 + /api/chat 直通 + 前端静态页。

一键启动（项目根执行）：
    .venv/Scripts/python.exe app/backend/main.py
浏览器打开 http://127.0.0.1:8000/

路径纪律（复用 cwd 实验#2 结论）：本文件是唯一入口，ROOT = parents[2]
算出项目根插入 sys.path——无论从哪个目录启动，agents.tools.* 都能导入。
"""
import sys
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))          # agents.tools.* 的导入链

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware


class NoCacheHTML(BaseHTTPMiddleware):
    """def 22 · HTML 永远拉新（Cache-Control no-cache）——根治"改了前端没生效"的缓存类问题；
    CSS/JS 等静态资源靠引用处的 ?v= 版本号管理。"""

    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        path = request.url.path
        if path == "/" or path.endswith(".html"):
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp

from agents.tools.search_shade import search_shade_tool
from agents.tools.foundation_search import foundation_search_tool
from agent_loop import agent_reply, agent_reply_stream      # def 11/29 · 大脑循环（function calling）+ 流式版
from tryon_service import run_tryon, run_face_profile     # def 12a/43 · 试妆 + 人脸属性档案（torch 全延迟导入）
from cvd_service import check_pair, preview_hex   # def 14 · 色盲视角（纯 numpy，零重依赖）
from cvd_service import correct_hex_for_profile             # def 17b · 试妆校色（档案反解）
from cvd_exam import start_exam, answer_exam, get_profile, calibrate, reset_profile   # def 17a/17b/50 · 色盲测评会话与校色确认 + 重启清档案
from products_service import match_product, custom_request, list_products, list_custom, catalog, cancel_custom, compare_library, reset_custom   # def 15d/18a/18d/18h/18i/50
from shade_review import shade_review   # def 27 · 社会视角守门（选色主流性判定+社会等效色+主流替代）


@asynccontextmanager
async def lifespan(_app):
    # def 50 · 重启 = 全新演示态（用户 2026-09-22）：运行态文件归零。
    # 放在预热前：预热约 60s 期间前端 state_clear.js 轮询 /api/health 即可拿到新 boot_id。
    reset_profile()
    reset_custom()
    print("[lifespan] 演示态已清空（CVD 档案 + 定制申请时间线）")
    # foundation 向量模型预热：不预热则首次粉底推荐要干等约 60s（bge 首载），预热后毫秒级。
    print("[lifespan] 预热 foundation 向量模型（首次约 60s，仅启动时一次）...")
    foundation_search_tool("预热", top_k=1)
    print("[lifespan] 预热完成")
    yield


app = FastAPI(title="ColorBoundless 工具测试台", lifespan=lifespan)

_BOOT_ID = str(time.time_ns())          # def 50 · 进程启动标识（重启必变，前端轮询比对）


@app.get("/api/health")
def api_health():
    """def 50 · 前端重启检测：state_clear.js 每 4s 轮询 boot_id，变化即清演示缓存并刷新。"""
    return {"ok": True, "boot_id": _BOOT_ID}
app.add_middleware(NoCacheHTML)


class ChatIn(BaseModel):
    message: str
    history: list = None   # def 22l · 多轮上下文 [{role: user|assistant, content: str}, ...] 最近 N 条


class CustomIn(BaseModel):
    hex: str
    region: str = "lip"
    note: str = ""


@app.get("/api/tools/search_shade")
def api_search_shade(hex: str, top_k: int = 5):
    """工具①：色号 → 最近官方色号"""
    return search_shade_tool(hex, top_k)


@app.get("/api/tools/foundation_search")
def api_foundation_search(query: str, brand: str = "", shade_level: str = "", top_k: int = 3):
    """工具②：集团粉底色号推荐（向量检索 + 品牌/明度档过滤）"""
    return foundation_search_tool(query, brand, shade_level, top_k)


@app.post("/api/chat")
def api_chat(body: ChatIn):
    """def 11 · 大脑循环版：自动选工具 → 代码执行 → 结果喂回 → 正文
       def 22l · 接入多轮 history——对话不再失忆（割裂修复）
       def 29 · 保留：内部调用（测评后自动总结）与流式不可用时的回退路径"""
    return agent_reply(body.message, body.history)


@app.post("/api/chat/stream")
def api_chat_stream(body: ChatIn):
    """def 29 · 流式对话（SSE）：首字 1~2s 上屏 + 工具轨迹实时可见。

    为什么：非流式下首字延迟 = 全部生成时间，flash 档生成 1500+ token 长回复
    要 40~90s，前端 90s 硬死线必炸且后端白烧 token（掐断了还在跑）。
    同步 generator 交给 StreamingResponse（FastAPI 自动 iterate_in_threadpool，
    不卡 event loop）；X-Accel-Buffering=no 防反代缓冲。
    """
    def _gen():
        for ev in agent_reply_stream(body.message, body.history):
            yield "data: " + json.dumps(ev, ensure_ascii=False) + "\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


MAX_IMG_BYTES = 10 * 1024 * 1024


@app.post("/api/tryon")
async def api_tryon(file: UploadFile = File(...), hex_color: str = Form(...),
                    alpha: float = Form(0.75), correct: bool = Form(True),
                    parts: str = Form("[]")):
    """def 12b/17b/15 · 试妆：multipart 照片 + 色号 + 强度 → 原图/上妆图 base64（五件套 JSON）

    def 17b · 校色联动：correct=True（默认）且存在测评档案时，主色号（唇）
    先反解为"标准视觉等意色"再上妆；校正过程与残差在 results.correction 里可解释。
    def 15 · parts = JSON 数组 [{"region": "lip|foundation|eyeshadow|brow",
    "hex": "#xxx", "alpha": 0.x}] 多部位聚合渲染；缺省 "[]" = 单唇模式（兼容 def 12）。
    校色只作用于唇部主色（foundation/eyeshadow 用原始所选色，v2 再做分部位校正）。
    """
    data = await file.read()
    if not data:
        return {"ok": False, "tool": "tryon", "error": "未收到图片数据", "results": {}}
    if len(data) > MAX_IMG_BYTES:
        return {"ok": False, "tool": "tryon", "error": "图片超过 10MB 限制", "results": {}}

    try:
        parts_list = json.loads(parts) if parts else None
        if parts_list is not None and not isinstance(parts_list, list):
            raise ValueError("parts 须为 JSON 数组")
    except (json.JSONDecodeError, ValueError) as e:
        return {"ok": False, "tool": "tryon", "error": f"parts 解析失败: {e}", "results": {}}

    # ---- def 17b · 校色组合层：流程纪律 = 测评 → 校色 → 试妆 ----
    hex_use = hex_color
    correction = {"applied": False,
                  "reason": "未启用校正" if not correct else "暂无可用测评档案或该档案无需校正"}
    if correct:
        prof = get_profile()
        if prof.get("ok"):
            pr = prof.get("results") or {}
            cal = pr.get("calibration")
            if not cal:
                correction = {"applied": False,
                              "reason": "尚未完成校色步骤——旅程为 测评 → 校色 → 试妆，"
                                        "请先在色盲校验页完成测评并选择校色模式"}
            elif not cal.get("enabled", True):   # def 34 · 启停位：开关未开不做反解（旧档案无此字段按开启对待）
                correction = {"applied": False,
                              "reason": "校色配置未启用（页面顶部「校色配色」开关未开），试妆色号不做反解"}
            elif cal.get("mode") != "correct":
                correction = {"applied": False,
                              "reason": f"当前校色模式为 {cal.get('mode')}，试妆色号不做反解"}
            else:
                try:
                    corrected, info = correct_hex_for_profile(hex_color, pr)
                    if info:
                        hex_use = corrected            # 仅在确实需要校正时替换色号
                        correction = info
                    else:
                        correction = {"applied": False,
                                      "reason": (pr.get("advice") or
                                                 "档案类型无需校正（normal/uncertain）")}
                except Exception as exc:   # 校正失败不阻塞试妆：退回原色并如实说明
                    correction = {"applied": False, "reason": f"校正计算失败，已用原色: {exc}"}

    # def 15 · 校色注入：反解后的主色只替换唇部 spec 的 hex（其余部位用原始所选色）
    if parts_list:
        for spec in parts_list:
            if isinstance(spec, dict) and spec.get("region", "lip") == "lip":
                spec["hex"] = hex_use

    # 线程池跑同步推理：冷启动约 30s（torch 全链+权重）也不卡 event loop，/api/chat 照常响应
    out = await run_in_threadpool(run_tryon, data, hex_use, alpha, parts_list)
    if out.get("ok"):
        out["results"]["correction"] = correction
        if correction.get("applied"):
            out["query"]["hex_requested"] = hex_color     # 用户所选（校正前）留痕
    return out


@app.post("/api/face_profile")
async def api_face_profile(file: UploadFile = File(...)):
    """def 43 · 人脸属性档案：上传照片 → 白平衡校正 + BiSeNet 部位解析 →
    肤色（hex+ITA 档位+冷暖底调）/ 发色 / 眉色 / 瞳色 / 唇色 / 脸型 结构化数据。
    前端上传后自动调用：渲染「AI 面部分析」面板，并作为事实上下文一键注入 AI 推荐
    （AI 不看图、不反问外貌——参数由代码检测填好，AI 只做推荐推理，省 token 提效率）。
    """
    data = await file.read()
    if not data:
        return {"ok": False, "tool": "face_profile", "error": "未收到图片数据", "results": {}}
    if len(data) > MAX_IMG_BYTES:
        return {"ok": False, "tool": "face_profile", "error": "图片超过 10MB 限制", "results": {}}
    return await run_in_threadpool(run_face_profile, data)


@app.get("/api/products/match")
def api_products_match(hex: str, region: str = "lip"):
    """def 15d · 所选色号 → 最近集团商品 + 有货/可定制判定（dE ≤ 5.0 有货）"""
    return match_product(hex, region)


@app.post("/api/products/custom")
def api_products_custom(body: CustomIn):
    """def 15d · 无现货色号 → 定制申请登记（data/products/custom_requests.json）"""
    return custom_request(body.hex, body.region, body.note)


@app.get("/api/products/list")
def api_products_list(region: str = "foundation"):
    """def 18a · 产品库全量列表（products 页浏览：lip 官方库 / foundation 集团库）"""
    return list_products(region)


@app.get("/api/products/custom/list")
def api_products_custom_list():
    """def 15d · 定制申请记录读取（products 页时间线，最新在前）"""
    return list_custom()


@app.post("/api/products/custom/cancel")
def api_products_custom_cancel(hex: str = "", region: str = "", ts: str = ""):
    """def 18h · 取消定制申请（试妆/产品库时间线：按 hex+region+ts 定位删除）"""
    return cancel_custom(hex, region, ts)


@app.get("/api/products/catalog")
def api_products_catalog():
    """def 18d · 商品橱窗：品类多窗口（口红1/2、粉底1/2、眼影1、腮红1）+ 色板切片"""
    return catalog()


@app.get("/api/products/compare")
def api_products_compare():
    """def 18i · 对比库：全商品颜色汇集（hex → 有此色的商品清单）+ 官方库覆盖标记"""
    return compare_library()


@app.get("/api/cvd/preview")
def api_cvd_preview(hex: str, cvd_type: str = "deuteranopia", severity: float = 1.0):
    """def 14 · 色盲视角预览：该色号在指定色觉缺陷用户眼中的等效颜色"""
    return preview_hex(hex, cvd_type, severity)


@app.get("/api/cvd/check")
def api_cvd_check(hex_a: str, hex_b: str, cvd_type: str = "deuteranopia"):
    """def 14 · 色对校验：正常 ΔE vs 模拟 ΔE + 规则库命中（avoid/safe）"""
    return check_pair(hex_a, hex_b, cvd_type)


class ExamAnswerIn(BaseModel):
    exam_id: str
    answer: object = None   # 石原=数字str / 网格=[row,col] / 排列=[显示位顺序]


class CalibrateIn(BaseModel):
    # def 34 · 配置导入与启停拆分：按钮只传 mode（导入），开关只传 enabled（启停）。
    # 显式 Optional（pydantic v2 不做 implicit optional 推断，str = None 传 null 会炸）
    mode: Optional[str] = None        # correct / simulate / off（导入配置时传）
    enabled: Optional[bool] = None    # 顶部开关启停位（True/False；与 mode 二选一）


class ShadeReviewIn(BaseModel):
    hex: str      # 用户所选色 #RRGGBB
    region: str   # lip / foundation / eyeshadow / brow / blush


@app.post("/api/cvd/exam/start")
def api_cvd_exam_start():
    """def 17a · 开新测评会话 → 第一题（12 题快筛：石原×2 + 网格×9 + 排列×1）"""
    return start_exam()


@app.post("/api/cvd/exam/answer")
def api_cvd_exam_answer(body: ExamAnswerIn):
    """def 17a · 收卷当前题 → 下一题 / done+色觉档案"""
    return answer_exam(body.exam_id, body.answer)


@app.get("/api/cvd/exam/profile")
def api_cvd_exam_profile():
    """def 17a · 最新色觉档案（AI 引导与校色的数据源）"""
    return get_profile()


@app.post("/api/cvd/exam/calibrate")
def api_cvd_exam_calibrate(body: CalibrateIn):
    """def 17b/34 · 校色确认：按钮传 mode=只导入配置；开关传 enabled=启停（二选一）"""
    return calibrate(body.mode, body.enabled)


@app.post("/api/tryon/shade_review")
def api_tryon_shade_review(body: ShadeReviewIn):
    """def 27 · 社会视角守门：选色主流性判定 + 正常人视角翻译 + 社会等效色 + 在售主流替代推荐"""
    return shade_review(body.hex, body.region)


# 前端静态页挂在 "/"，必须放在 API 路由之后定义（先注册的先匹配）
_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(_FRONTEND), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
