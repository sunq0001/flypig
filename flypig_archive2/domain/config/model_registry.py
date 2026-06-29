"""模型注册表 — 模型名 → 提供商/接口 的动态映射

注意事项：
- 注册表只定义模型元数据（provider、base_url、model 接口名），不包含价格
- 默认模型名从 config.yaml 的 llm.default_model 读取，不在本文件中硬编码
- 前端聊天发送消息时必须带上 model 参数，后端拒绝不传 model 的请求
- 新增模型只需在此注册，无需改其他代码
- 价格数据见 data/pricing_defaults.json + data/pricing_cache.json
"""

from pathlib import Path

# 国产模型优先，均兼容 OpenAI API 格式
REGISTRY = {
    # ── 国际 ──
    "deepseek-v4-flash": {
        "provider": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    "deepseek-v4-pro": {
        "provider": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-reasoner",
    },
    "gpt-4o-mini": {
        "provider": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "gpt-4o": {
        "provider": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
    },
    "claude-3-5-sonnet": {
        "provider": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "model": "claude-3-5-sonnet-20241022",
    },
    # ── 阿里 通义千问 ──
    "qwen-turbo": {
        "provider": "Qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-turbo",
    },
    "qwen-plus": {
        "provider": "Qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "qwen-max": {
        "provider": "Qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-max",
    },
    # ── 腾讯 混元 ──
    "hunyuan-pro": {
        "provider": "Tencent",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "model": "hunyuan-pro",
    },
    "hunyuan-standard": {
        "provider": "Tencent",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "model": "hunyuan-standard",
    },
    # ── 字节 豆包 ──
    "doubao-pro-32k": {
        "provider": "ByteDance",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-pro-32k",
    },
    "doubao-lite-32k": {
        "provider": "ByteDance",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-lite-32k",
    },
    # ── Kimi 月之暗面 ──
    "kimi-k2.5": {
        "provider": "Moonshot",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "kimi-k2.5",
    },
    "moonshot-v1-8k": {
        "provider": "Moonshot",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
    },
    # ── GLM 智谱 ──
    "glm-4-plus": {
        "provider": "ZhipuAI",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-plus",
    },
    "glm-4-air": {
        "provider": "ZhipuAI",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-air",
    },
    "glm-4-flash": {
        "provider": "ZhipuAI",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
    },
    # ── 本地模型（Ollama）动态发现 ──
    # 见 get_local_models()，运行时会查询 Ollama API 获取已安装的模型
}


# Ollama 可执行文件路径（自动检测）
OLLAMA_PATH = None
for _p in [
    r"C:\Users\mss\AppData\Local\Programs\Ollama\ollama.exe",
    "/usr/local/bin/ollama",
    "/usr/bin/ollama",
]:
    if Path(_p).exists():
        OLLAMA_PATH = Path(_p)
        break


def resolve(name: str) -> dict | None:
    """按友好名称查找模型注册信息"""
    return REGISTRY.get(name)


def known_models() -> list[str]:
    """返回所有注册的模型名列表"""
    return list(REGISTRY.keys())


def providers() -> set[str]:
    """返回所有提供商集合"""
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
        models = data.get("models", [])
        result = []
        for m in models:
            name = m.get("name", "")
            if not name:
                continue
            result.append({
                "name": name,
                "provider": "Local",
                "base_url": "http://localhost:11434/v1",
                "api_model": name,
                "local": True,
                "has_key": True,
            })

        _LOCAL_CACHE["models"] = result
        _LOCAL_CACHE["ts"] = now
        return result
    except Exception:
        return []
