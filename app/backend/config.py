# -*- coding: utf-8 -*-
"""配置中枢（def 45 · 环境变量版）：大模型的 key / 地址 / 模型名全部走环境变量。

为什么从配置文件改为环境变量（用户 2026-09-22 定稿：防泄露与 api 盗用）：
  - key 只存在于 os.environ 与 .env（.gitignore 已排除，永不入库、不随项目打包外流）
  - 仓库内任何文件都不再有明文密钥——llm.local.json / secrets.local.json 已删除退役
  - 12-factor 惯例：换环境/换 key 不动任何入库文件；部署平台直接配环境变量即可

读取：
  1. import config 时自动加载同目录 .env（真实环境变量优先，.env 不覆盖已有变量）
  2. LLM_PROVIDER 选激活引擎；LLM_<名字>_API_KEY / _BASE_URL / _MODEL 给三件套
  3. base_url / model 缺省用内置预设（非敏感，见 _PRESETS）；api_key 缺省 = 空
校验：云端引擎 key 必填（fail fast）；本地 127.0.0.1 引擎 key 可空；model 必填。
"""
import os
from pathlib import Path
from urllib.parse import urlparse

_BACKEND_DIR = Path(__file__).resolve().parent
ENV_PATH = _BACKEND_DIR / ".env"                    # 唯一秘密载体（.gitignore 已排除）
EXAMPLE_PATH = _BACKEND_DIR / ".env.example"        # 入库模板

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}

# 内置非敏感预设：base_url / model / thinking。key 永远不写在这里——只走环境变量。
_PRESETS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-v4-flash",
        "thinking": {"type": "disabled"},      # def 22 · 关思维链，响应更快
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "model": "glm-5.3-flash",
        # def 44 · GLM 5.3-flash 服务端已改"始终思考"：{"type":"disabled"} 与
        # {"type":"low"} 均被拒（HTTP 400 code 1210，实测 2026-09-22）——
        # 最稳姿势是不发送 thinking 字段（null）；思维链走 reasoning_content，
        # llm_client 已剥离不上屏。非流式 max_tokens 需给足（见 def 8 注释）。
        "thinking": None,
    },
    # def 44 · 本地大模型预设：OpenAI 兼容端点，api_key 留空（无鉴权）。
    # thinking: null = 不发送 GLM 专有字段（llama.cpp/ollama 不认识）。
    "llamacpp": {
        "base_url": "http://127.0.0.1:8080/v1/chat/completions",
        "model": "",                           # 在 .env 里填 LLM_LLAMACPP_MODEL（加载的 gguf 名）
        "thinking": None,
    },
    "ollama": {
        "base_url": "http://127.0.0.1:11434/v1/chat/completions",
        "model": "",                           # 在 .env 里填 LLM_OLLAMA_MODEL（如 qwen2.5:7b）
        "thinking": None,
    },
}

_ENV_SUFFIXES = ("_API_KEY", "_BASE_URL", "_MODEL")


def _load_dotenv(path: Path = ENV_PATH) -> int:
    """def 45 · 最小 .env 解析：KEY=VALUE、# 注释、去引号；不覆盖已有环境变量。

    返回载入 os.environ 的变量数。为什么手写而不引 python-dotenv：
    项目零第三方依赖惯例（HTTP 都用 urllib 手写），十几行能解决的事不进 requirements。
    """
    if not path.exists():
        return 0
    n = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'").strip()
        if k and k not in os.environ:          # 真环境变量优先于 .env（部署时可覆盖）
            os.environ[k] = v
            n += 1
    return n


_load_dotenv()      # import 即生效：任何模块 import config 后，.env 已进环境


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def load_secrets() -> dict:
    """def 45 · 从环境变量组装有效配置并校验当前 provider（fail fast，说人话报错）。

    返回形状与 def 7 兼容：{"provider": str, "providers": {name: {...}}}。
    """
    provider = _env("LLM_PROVIDER") or "deepseek"
    names = set(_PRESETS) | {
        k[4:].split("_", 1)[0].lower()
        for k in os.environ
        if k.startswith("LLM_") and k.endswith(_ENV_SUFFIXES)
    }
    providers = {}
    for name in names:
        p = dict(_PRESETS.get(name) or {"base_url": "", "model": "", "thinking": None})
        up = name.upper()
        p["api_key"] = _env(f"LLM_{up}_API_KEY")
        p["base_url"] = _env(f"LLM_{up}_BASE_URL") or p["base_url"]
        p["model"] = _env(f"LLM_{up}_MODEL") or p["model"]
        providers[name] = p

    if provider not in providers:
        raise RuntimeError(
            f"LLM_PROVIDER={provider!r} 不可用——可用引擎：{sorted(providers)}；"
            f"云端引擎需在 {ENV_PATH.name} 里填对应 LLM_<名字>_API_KEY（模板见 {EXAMPLE_PATH.name}）")
    cur = providers[provider]
    host = (urlparse(cur["base_url"]).hostname or "").lower()
    if not cur["model"]:
        raise RuntimeError(
            f"provider={provider} 的 model 为空——请在 {ENV_PATH.name} 里填 "
            f"LLM_{provider.upper()}_MODEL（本地 llama.cpp 填加载的 gguf 名；"
            f"ollama 填 pull 的名字，如 qwen2.5:7b）")
    if not host:
        raise RuntimeError(
            f"provider={provider} 的 base_url 不合法: {cur['base_url']!r}（需 http(s):// 开头，"
            f"可用 LLM_{provider.upper()}_BASE_URL 环境变量指定）")
    if not cur["api_key"] and host not in _LOCAL_HOSTS:
        raise RuntimeError(
            f"provider={provider} 的 api_key 为空——云端服务必填（本地 127.0.0.1 服务可留空）。"
            f"请在 {ENV_PATH.name} 里填 LLM_{provider.upper()}_API_KEY，或设置同名环境变量")
    return {"provider": provider, "providers": providers}


def current_provider(cfg: dict = None) -> dict:
    """def 7 附带 · 取当前 provider 的三件套 {base_url, api_key, model}。"""
    cfg = cfg or load_secrets()
    return cfg["providers"][cfg["provider"]]

