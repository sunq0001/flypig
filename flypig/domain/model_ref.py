"""模型注册表 — 模型名 → 提供商/接口 的动态映射

为什么做：模型名（如 deepseek-v4-flash）需要映射到实际的 API 地址和提供商，
前端选模型时供后端路由到正确的接口。

实现方法：REGISTRY 字典 + resolve()/known_models()/providers() 辅助函数。

层&amp;依赖：domain 层，零依赖
"""

from pathlib import Path

# 国产模型优先，均兼容 OpenAI API 格式
REGISTRY = {
    # ── 国际 ──
    "deepseek-v4-flash": {"provider": "DeepSeek", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "deepseek-v4-pro": {"provider": "DeepSeek", "base_url": "https://api.deepseek.com", "model": "deepseek-reasoner"},
    "gpt-4o-mini": {"provider": "OpenAI", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "gpt-4o": {"provider": "OpenAI", "base_url": "https://api.openai.com/v1", "model": "gpt-4o"},
    "claude-3-5-sonnet": {"provider": "Anthropic", "base_url": "https://api.anthropic.com", "model": "claude-3-5-sonnet-20241022"},
    # ── 阿里 ──
    "qwen-turbo": {"provider": "Qwen", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-turbo"},
    "qwen-plus": {"provider": "Qwen", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
    "qwen-max": {"provider": "Qwen", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-max"},
    # ── 腾讯 ──
    "hunyuan-pro": {"provider": "Tencent", "base_url": "https://api.hunyuan.cloud.tencent.com/v1", "model": "hunyuan-pro"},
    "hunyuan-standard": {"provider": "Tencent", "base_url": "https://api.hunyuan.cloud.tencent.com/v1", "model": "hunyuan-standard"},
    # ── 字节 ──
    "doubao-pro-32k": {"provider": "ByteDance", "base_url": "https://ark.cn-beijing.volces.com/api/v3", "model": "doubao-pro-32k"},
    "doubao-lite-32k": {"provider": "ByteDance", "base_url": "https://ark.cn-beijing.volces.com/api/v3", "model": "doubao-lite-32k"},
    # ── Kimi ──
    "kimi-k2.5": {"provider": "Moonshot", "base_url": "https://api.moonshot.cn/v1", "model": "kimi-k2.5"},
    "moonshot-v1-8k": {"provider": "Moonshot", "base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"},
    # ── GLM ──
    "glm-4-plus": {"provider": "ZhipuAI", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-plus"},
    "glm-4-air": {"provider": "ZhipuAI", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-air"},
    "glm-4-flash": {"provider": "ZhipuAI", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash"},
}


OLLAMA_PATH = None
for _p in [
    r"C:\Users\mss\AppData\Local\Programs\Ollama\ollama.exe",
    "/usr/local/bin/ollama", "/usr/bin/ollama",
]:
    if Path(_p).exists():
        OLLAMA_PATH = Path(_p)
        break


def resolve(name: str) -> dict | None:
    return REGISTRY.get(name)


def known_models() -> list[str]:
    return list(REGISTRY.keys())


def providers() -> set[str]:
    return {m["provider"] for m in REGISTRY.values()}


_LOCAL_CACHE = {"models": [], "ts": 0}


def get_local_models() -> list[dict]:
    """从 Ollama API 动态获取已安装的本地模型列表（缓存 30 秒）"""
    import time
    now = time.time()
    if now - _LOCAL_CACHE["ts"] < 30:
        return _LOCAL_CACHE["models"]

    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code != 200:
            return []

        data = resp.json()
        result = []
        for m in data.get("models", []):
            name = m.get("name", "")
            if not name:
                continue
            result.append({
                "name": name, "provider": "Local",
                "base_url": "http://localhost:11434/v1",
                "api_model": name, "local": True, "has_key": True,
            })

        _LOCAL_CACHE["models"] = result
        _LOCAL_CACHE["ts"] = now
        return result
    except Exception:
        return []
