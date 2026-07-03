"""AppSettings — 应用配置加载（pydantic-settings + YAML）

为什么不硬编码默认值：所有配置数据来自 data/model_registry.json，
包括 API Key 映射、Ollama 默认地址等。代码只负责加载逻辑，不存储数据。

实现方法：pydantic-settings 的 BaseSettings 自动从环境变量读取，
PyYAML 从 config.yaml 加载持久化配置，JSON 提供默认值。
优先级：环境变量 > YAML > JSON 默认值。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import yaml
from pydantic_settings import BaseSettings


def _load_json_config(key: str, sub_key: str = None, default=None):
    """从 model_registry.json 读取配置"""
    path = Path(__file__).resolve().parent.parent / "data" / "model_registry.json"
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        section = raw.get(key, {})
        if sub_key:
            return section.get(sub_key, default)
        return section
    except Exception:
        return default


class AppSettings(BaseSettings):
    """pydantic-settings 模型: 环境变量覆盖 YAML 覆盖 JSON 默认值"""

    # ── LLM ──
    default_model: str = "deepseek-v4-flash"
    deepseek_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    qwen_api_key: Optional[str] = None
    hunyuan_api_key: Optional[str] = None
    doubao_api_key: Optional[str] = None
    moonshot_api_key: Optional[str] = None
    zhipu_api_key: Optional[str] = None

    # ── 本地模型（默认值来自 JSON local.default_ollama_url）──
    ollama_base_url: str = ""

    # ── 应用 ──
    workspace: Optional[str] = None
    log_level: str = "DEBUG"
    data_dir: str = ""

    model_config = {"env_prefix": "flypig_", "extra": "ignore"}


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
