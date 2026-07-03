"""AppSettings — 应用配置加载（pydantic-settings + YAML）

注意：AppSettings 类定义在 shared/settings.py 中，此处只负责加载逻辑。
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings  # noqa: F401 保持依赖

from flypig.shared.settings import AppSettings


def load_config(config_path: str | Path | None = None) -> AppSettings:
    """加载配置: 环境变量 > YAML > JSON 默认值"""
    # 先拿 JSON 默认值覆盖 AppSettings 的 Python 默认
    json_default = _load_json_config("local", "default_ollama_url") or ""
    settings = AppSettings(ollama_base_url=json_default)

    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent.parent / "config.yaml"
    config_path = Path(config_path)

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            data: dict = yaml.safe_load(f) or {}

        llm = data.get("llm", {})
        agent = data.get("agent", {})
        api_keys = data.get("api_keys", {})

        if not settings.default_model or settings.default_model == "deepseek-v4-flash":
            yaml_model = llm.get("default_model")
            if yaml_model:
                settings.default_model = yaml_model

        if not settings.workspace:
            ws = agent.get("workspace")
            if ws and ws != "~":
                settings.workspace = ws

        # 从 JSON 加载厂商→属性映射，从 YAML 填充 API Key
        provider_key_map = _load_json_config("models", sub_key=None, default={})
        if provider_key_map and isinstance(provider_key_map, dict):
            seen = {}
            for name, meta in provider_key_map.items():
                provider = meta.get("provider", "")
                attr = meta.get("key_attr", "")
                if provider and attr:
                    seen[provider] = attr
            for provider, attr in seen.items():
                if not getattr(settings, attr):
                    val = api_keys.get(provider)
                    if val:
                        setattr(settings, attr, val)

    return settings
