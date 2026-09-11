# -*- coding: utf-8 -*-
"""配置中枢：读 secrets.local.json（.gitignore 已排除，永不入库）。

为什么要独立配置层：base_url / api_key / model 三件套随 provider 切换，
代码只认"OpenAI 兼容协议"——换大脑 = 改配置文件，不改一行代码
（R-02 决策的精神延续：vLLM/智谱/DeepSeek 都是可插拔的引擎）。
"""
import json
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
SECRETS_PATH = _BACKEND_DIR / "secrets.local.json"

_DEFAULTS = {
    "provider": "deepseek",
    "providers": {
        "deepseek": {
            "base_url": "https://api.deepseek.com/chat/completions",
            "api_key": "",
            "model": "deepseek-v4-flash",
        },
        "zhipu": {
            "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            "api_key": "",
            "model": "glm-5.3-flash",
        },
    },
}


def load_secrets(path: Path = SECRETS_PATH) -> dict:
    """def 7 · 读配置并与默认值深合并，启动时校验当前 provider 可用。

    三种失败都说人话（RuntimeError），让 FastAPI 启动那一刻就报清楚，
    而不是等第一次对话才炸（fail fast，与 shade_library 同哲学）。
    """
    if not path.exists():
        raise RuntimeError(f"缺少配置文件: {path}")
    try:
        user = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"配置文件不是合法 JSON: {path} -> {e}")

    cfg = json.loads(json.dumps(_DEFAULTS))          # 深拷贝默认值
    cfg.update({k: v for k, v in user.items() if not k.startswith("_")})
    for name, p in user.get("providers", {}).items():
        cfg["providers"].setdefault(name, {}).update(p)

    provider = cfg.get("provider")
    if provider not in cfg["providers"]:
        raise RuntimeError(f"provider 只能是 {list(cfg['providers'])}，收到 {provider!r}")
    cur = cfg["providers"][provider]
    if not cur.get("api_key"):
        raise RuntimeError(
            f"provider={provider} 的 api_key 为空——请填写 {path.name} 后重启服务")
    if not str(cur.get("base_url", "")).startswith("http"):
        raise RuntimeError(f"provider={provider} 的 base_url 不合法: {cur.get('base_url')!r}")
    return cfg


def current_provider(cfg: dict = None) -> dict:
    """def 7 附带 · 取当前 provider 的三件套 {base_url, api_key, model}。"""
    cfg = cfg or load_secrets()
    return cfg["providers"][cfg["provider"]]
