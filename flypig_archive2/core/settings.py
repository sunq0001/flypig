"""AppConfig — 应用配置加载（pydantic-settings + YAML）

为什么做：配置（默认模型、API Key、项目路径等）散落在环境变量、YAML 文件中，
需要一个统一的加载入口，按 env var > YAML > 默认值 的优先级合并。

实现方法：pydantic-settings 的 BaseSettings 自动从环境变量读取，
PyYAML 从 config.yaml 加载持久化配置，两者合并后输出最终配置对象。

实现效果：改一个环境变量或 config.yaml 即可控制全局行为，不用翻代码改常量。

技术栈：pydantic-settings, PyYAML, python-dotenv

层&依赖：core 层（无业务依赖），纯配置加载，不依赖任何业务模块
细节见文档：docs/docs_refactor/backend-modules.md → §配置即代码、tech-stack.md → §配置
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
    """加载配置: 环境变量 > YAML > 默认值

    1. 用 pydantic-settings 从环境变量读取 (FLYPIG_*)
    2. 从 config.yaml 读取持久化配置
    3. 两者合并，环境变量优先级更高
    """
    # Step 1: 环境变量
    settings = AppSettings()

    # Step 2: YAML 配置文件
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    config_path = Path(config_path)

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            data: dict = yaml.safe_load(f) or {}

        llm = data.get("llm", {})
        agent = data.get("agent", {})
        api_keys = data.get("api_keys", {})

        # 环境变量未设置时从 YAML 读取
        if not settings.default_model or settings.default_model == "deepseek-v4-flash":
            yaml_model = llm.get("default_model")
            if yaml_model:
                settings.default_model = yaml_model

        if not settings.workspace:
            ws = agent.get("workspace")
            if ws and ws != "~":
                settings.workspace = ws

        if not settings.deepseek_api_key:
            settings.deepseek_api_key = api_keys.get("DeepSeek")
        if not settings.openai_api_key:
            settings.openai_api_key = api_keys.get("OpenAI")
        if not settings.anthropic_api_key:
            settings.anthropic_api_key = api_keys.get("Anthropic")
        if not settings.qwen_api_key:
            settings.qwen_api_key = api_keys.get("Qwen")
        if not settings.hunyuan_api_key:
            settings.hunyuan_api_key = api_keys.get("Tencent")
        if not settings.doubao_api_key:
            settings.doubao_api_key = api_keys.get("ByteDance")
        if not settings.moonshot_api_key:
            settings.moonshot_api_key = api_keys.get("Moonshot")
        if not settings.zhipu_api_key:
            settings.zhipu_api_key = api_keys.get("ZhipuAI")

    return settings
