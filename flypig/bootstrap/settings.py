"""settings

为什么做：应用配置需要从环境变量 / YAML / JSON 三级加载，不能硬编码

实现方法：AppSettings(pydantic-settings) 自动从环境变量读取，PyYAML 从 config.yaml 加载，JSON 提供默认值。优先级：环境变量 > YAML > JSON

层&依赖：bootstrap 层，依赖 shared.settings
"""

from __future__ import annotations

from pathlib import Path

import yaml
from flypig.shared.settings import AppSettings
from pydantic_settings import BaseSettings  # noqa: F401 保持依赖


def _apply_yaml_llm(settings: AppSettings, data: dict) -> None:
    """从 YAML 的 llm 段覆盖 default_model"""
    llm = data.get("llm", {})
    if not settings.default_model or settings.default_model == "deepseek-v4-flash":
        yaml_model = llm.get("default_model")
        if yaml_model:
            settings.default_model = yaml_model


def _apply_yaml_agent(settings: AppSettings, data: dict) -> None:
    """从 YAML 的 agent 段覆盖 workspace"""
    agent = data.get("agent", {})
    if not settings.workspace:
        ws = agent.get("workspace")
        if ws and ws != "~":
            settings.workspace = ws


def _apply_yaml_api_keys(settings: AppSettings, data: dict) -> None:
    """从 YAML 的 api_keys 段和 JSON 模型映射填充各厂商 API Key"""
    api_keys = data.get("api_keys", {})
    provider_key_map = _load_json_config("models", sub_key=None, default={})
    if not provider_key_map or not isinstance(provider_key_map, dict):
        return
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


def _apply_yaml_config(settings: AppSettings, data: dict) -> None:
    """将 YAML 配置各段依次应用到 settings 对象"""
    _apply_yaml_llm(settings, data)
    _apply_yaml_agent(settings, data)
    _apply_yaml_api_keys(settings, data)


def load_config(config_path: str | Path | None = None) -> AppSettings:
    """加载配置: 环境变量 > YAML > JSON 默认值"""
    # 先拿 JSON 默认值覆盖 AppSettings 的 Python 默认
    json_default = _load_json_config("local", "default_ollama_url") or ""
    settings = AppSettings(ollama_base_url=json_default)

    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent.parent / "config.yaml"
    config_path = Path(config_path)

    if not config_path.exists():
        return settings

    with open(config_path, encoding="utf-8") as f:
        data: dict = yaml.safe_load(f) or {}

    _apply_yaml_config(settings, data)
    return settings
