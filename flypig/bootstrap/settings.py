"""settings

为什么做：应用配置需要从环境变量 / YAML / JSON 三级加载，不能硬编码

实现方法：AppSettings(pydantic-settings) 自动从环境变量读取，PyYAML 从 config.yaml 加载，JSON 提供默认值。优先级：环境变量 > YAML > JSON

层&依赖：bootstrap 层，依赖 shared.settings
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings  # noqa: F401 保持依赖

from flypig.shared.settings import AppSettings


def _load_json_config(section: str, sub_key: str | None = None, default: Any = None) -> Any:
    """从 model_registry.json 读取指定段的值

    Args:
        section: 顶层段名，如 "local"、"models"
        sub_key: 段内子键，为 None 则返回整个段
        default: 缺省返回值

    Returns:
        配置值或 default
    """
    reg_path = (
        Path(__file__).resolve().parent.parent.parent / "flypig" / "data" / "model_registry.json"
    )
    if not reg_path.exists():
        return default
    try:
        with open(reg_path, encoding="utf-8") as f:
            data: dict = json.load(f)
    except Exception:
        return default
    section_data = data.get(section)
    if section_data is None:
        return default
    if sub_key is None:
        return section_data
    return section_data.get(sub_key, default)


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
    for meta in provider_key_map.values():
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


def _load_persisted_api_keys(settings: AppSettings) -> None:
    """从 data/api_keys.json 加载 UI 保存的 API Key（优先级高于 YAML，低于环境变量）

    委托给 infrastructure.persistence.api_key_file_repo 的公共函数，
    自身不实现任何文件读/写逻辑。
    """
    from flypig.infrastructure.persistence.api_key_file_repo import load_api_keys_from_file

    keys = load_api_keys_from_file()
    if not keys:
        return
    # 从 model_registry.json 读 provider → key_attr 映射
    provider_key_map = _load_json_config("models", sub_key=None, default={})
    if not isinstance(provider_key_map, dict):
        return
    seen: dict[str, str] = {}
    for meta in provider_key_map.values():
        p = meta.get("provider", "")
        attr = meta.get("key_attr", "")
        if p and attr:
            seen[p] = attr
    for provider, key in keys.items():
        attr = seen.get(provider, "")
        if attr and hasattr(settings, attr) and not getattr(settings, attr):
            setattr(settings, attr, key)


def load_config(config_path: str | Path | None = None) -> AppSettings:
    """加载配置: 环境变量 > UI 保存的 Key > YAML > JSON 默认值"""
    # 先拿 JSON 默认值覆盖 AppSettings 的 Python 默认
    json_default = _load_json_config("local", "default_ollama_url") or ""
    settings = AppSettings(ollama_base_url=json_default)

    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent.parent / "config.yaml"
    config_path = Path(config_path)

    if not config_path.exists():
        _load_persisted_api_keys(settings)
        return settings

    with open(config_path, encoding="utf-8") as f:
        data: dict = yaml.safe_load(f) or {}

    _apply_yaml_config(settings, data)
    _load_persisted_api_keys(settings)  # UI 保存的 Key 覆盖 YAML（但低于环境变量）
    return settings
