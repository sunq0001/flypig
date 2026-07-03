"""模型注册表 — 从 model_registry.json 加载所有配置

为什么做：模型名（如 deepseek-v4-flash）需要映射到实际的 API 地址、提供商元数据等，
前端选模型时供后端路由到正确的接口。

实现方法：所有配置数据来自 data/model_registry.json，代码只负责加载和转发。
包括模型定义、厂商元数据、Pricing API 配置、本地模型配置等全部在 JSON 中。
本地模型通过 acl.ollama.OllamaACL 动态获取，domain 层不直接调 httpx。

层&依赖：domain 层
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_MODEL_REGISTRY_PATH = _DATA_DIR / "model_registry.json"


def load_registry() -> dict:
    """返回 model_registry.json 的完整内容"""
    with open(_MODEL_REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load():
    """从 JSON 加载注册表，构建 REGISTRY 和 PROVIDER_KEY_MAP"""
    raw = load_registry()

    models_raw = raw.get("models", {})
    _REGISTRY = dict(models_raw)

    _PROVIDER_KEY_MAP = {}
    for name, meta in models_raw.items():
        provider = meta.get("provider", "")
        key_attr = meta.get("key_attr", "")
        if provider and key_attr:
            _PROVIDER_KEY_MAP[provider] = key_attr

    return _REGISTRY, _PROVIDER_KEY_MAP


REGISTRY, PROVIDER_KEY_MAP = _load()


def resolve(name: str) -> dict | None:
    return REGISTRY.get(name)


def known_models() -> list[str]:
    return list(REGISTRY.keys())


def get_provider_meta(name: str) -> dict | None:
    """获取某个模型的厂商元数据（icon/color/display_name）"""
    meta = REGISTRY.get(name)
    if not meta:
        return None
    return {
        "icon": meta.get("icon", ""),
        "color": meta.get("color", ""),
        "display_name": meta.get("display_name", ""),
    }


def get_pricing_config() -> dict:
    """获取 pricing 配置段"""
    raw = load_registry()
    return raw.get("pricing", {})


def get_local_config() -> dict:
    """获取 local 配置段（本地模型元数据）"""
    raw = load_registry()
    return raw.get("local", {})


def get_portkey_provider(model_name: str) -> str:
    """获取模型的 Portkey 提供商名（有覆盖走覆盖，否则 provider.lower()）"""
    meta = REGISTRY.get(model_name, {})
    override = meta.get("portkey_provider")
    if override:
        return override
    return meta.get("provider", "").lower()
