"""AppSettings — 应用配置模型（共享内核）

为什么做：AppSettings 被 application 层和 infrastructure 层引用，
定义在 shared 层避免各层依赖 bootstrap。

依赖说明：pydantic-settings 是所有层都需要的，因此放在 shared 是合理的。
"""

from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings


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

    # ── 本地模型 ──
    ollama_base_url: str = ""

    # ── 应用 ──
    workspace: Optional[str] = None
    log_level: str = "DEBUG"
    data_dir: str = ""

    model_config = {"env_prefix": "flypig_", "extra": "ignore"}
