"""AppSettings — 应用配置加载（pydantic-settings + YAML）

为什么做：配置（默认模型、API Key、项目路径等）散落在环境变量、YAML 文件中，
需要一个统一的加载入口，按 env var > YAML > 默认值 的优先级合并。

实现方法：pydantic-settings 的 BaseSettings 自动从环境变量读取，
PyYAML 从 config.yaml 加载持久化配置，两者合并后输出最终配置对象。

实现效果：改一个环境变量或 config.yaml 即可控制全局行为，不用翻代码改常量。

层&amp;依赖：bootstrap 层（无业务依赖），纯配置加载
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """pydantic-settings 模型: 环境变量覆盖 YAML 配置"""

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

    # ── 应用 ──
    workspace: Optional[str] = None
    log_level: str = "DEBUG"
    data_dir: str = ""

    model_config = {"env_prefix": "flypig_", "extra": "ignore"}


def load_config(config_path: str | Path | None = None) -> AppSettings:
    """加载配置: 环境变量 > YAML > 默认值"""
    settings = AppSettings()

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

        key_mapping = {
            "deepseek_api_key": "DeepSeek", "openai_api_key": "OpenAI",
            "anthropic_api_key": "Anthropic", "qwen_api_key": "Qwen",
            "hunyuan_api_key": "Tencent", "doubao_api_key": "ByteDance",
            "moonshot_api_key": "Moonshot", "zhipu_api_key": "ZhipuAI",
        }
        for attr, yaml_key in key_mapping.items():
            if not getattr(settings, attr):
                val = api_keys.get(yaml_key)
                if val:
                    setattr(settings, attr, val)

    return settings
