"""模型注册表 — 模型名 → 提供商/接口 的动态映射

注意事项：
- 注册表只定义模型元数据（提供商、base_url、接口模型名），不定义"默认用哪个模型"
- 默认模型名从 config.yaml 的 llm.default_model 读取，不在本文件中硬编码
- 前端聊天发送消息时必须带上 model 参数，后端拒绝不传 model 的请求
- 界面 model-bar 显示哪个模型 = 后端 /api/config 返回的 default_model，前端不假设
- 新增模型只需在此注册，无需改其他代码
"""

REGISTRY = {
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
}


def resolve(name: str) -> dict | None:
    return REGISTRY.get(name)


def known_models() -> list[str]:
    return list(REGISTRY.keys())


def providers() -> set[str]:
    return {m["provider"] for m in REGISTRY.values()}
