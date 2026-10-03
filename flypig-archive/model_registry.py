"""模型注册表 — 模型名 → 提供商/接口/环境变量 的动态映射"""

from typing import Optional

# ============================================================
# 模型元数据注册表
# 添加新模型只需在这里加一行，config.yaml 里写名字就行
# ============================================================
REGISTRY = {
    # ── DeepSeek ──
    "deepseek-v4-flash": {
        "provider": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "env_key": "DEEPSEEK_API_KEY",
        "model": "deepseek-v4-flash",
    },
    "deepseek-v4-pro": {
        "provider": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "env_key": "DEEPSEEK_API_KEY",
        "model": "deepseek-v4-pro",
    },
    # ── OpenAI ──
    "gpt-4o-mini": {
        "provider": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
    },
    "gpt-4o": {
        "provider": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "model": "gpt-4o",
    },
    # ── Anthropic ──
    "claude-3-5-haiku": {
        "provider": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "env_key": "ANTHROPIC_API_KEY",
        "model": "claude-3-5-haiku",
    },
    "claude-3-5-sonnet": {
        "provider": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "env_key": "ANTHROPIC_API_KEY",
        "model": "claude-3-5-sonnet",
    },
    "claude-4-opus": {
        "provider": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "env_key": "ANTHROPIC_API_KEY",
        "model": "claude-4-opus",
    },
}

# ============================================================
# 提供商信息
# ============================================================
PROVIDER_INFO = {
    "DeepSeek": {
        "console_url": "https://platform.deepseek.com/api_keys",
    },
    "OpenAI": {
        "console_url": "https://platform.openai.com/api-keys",
    },
    "Anthropic": {
        "console_url": "https://console.anthropic.com/settings/keys",
    },
}


def resolve(name: str) -> Optional[dict]:
    """根据模型名解析出完整元数据"""
    return REGISTRY.get(name)


def known_models() -> list:
    """返回所有已注册的模型名"""
    return list(REGISTRY.keys())


def providers() -> set:
    """返回所有已知提供商"""
    return {m["provider"] for m in REGISTRY.values()}


def models_by_provider(provider: str) -> list:
    """返回指定提供商的所有模型名"""
    return [n for n, m in REGISTRY.items() if m["provider"] == provider]


def provider_info(name: str) -> Optional[dict]:
    """返回提供商信息（控制台 URL 等）"""
    return PROVIDER_INFO.get(name)
