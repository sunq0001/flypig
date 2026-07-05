"""openai_adapter

为什么做：OpenAI 兼容格式的 LLM API（DeepSeek/Qwen/GLM/豆包等）需要统一适配器

实现方法：封装 AsyncOpenAI SDK，stream 方法返回异步 token 生成器。配置来自 model_registry.json + AppSettings

层&依赖：infrastructure.llm 层，实现 domain.interfaces.imodel
"""

from __future__ import annotations

from typing import Any

from flypig.domain.exceptions import ModelAPIError
from flypig.domain.interfaces.imodel import IModel
from flypig.domain.registry import ModelRegistry
from flypig.shared.settings import AppSettings
from openai import AsyncOpenAI


class OpenAIAdapter(IModel):
    """OpenAI 兼容格式的 LLM 适配器"""

    def __init__(
        self,
        model_name: str,
        settings: AppSettings | None = None,
        registry: ModelRegistry | None = None,
    ):
        self._model_name = model_name
        self._registry = registry or ModelRegistry()

        meta = self._registry.resolve(model_name)
        if meta:
            self._provider = meta["provider"]
            self._base_url = meta["base_url"]
            self._api_model = meta["api_model"]
            is_local = meta.get("local", False)
        else:
            local = self._registry.get_local_config()
            self._provider = local.get("provider", "Local")
            api_path = local.get("api_path", "/v1")
            base_url = (
                settings.ollama_base_url or local.get("default_ollama_url", "") if settings else ""
            )
            self._base_url = f"{base_url}{api_path}"
            self._api_model = model_name
            is_local = True

        if is_local:
            api_key = "not-needed"
        else:
            api_key = self._resolve_api_key(settings, self._provider)
            if not api_key:
                raise ModelAPIError(f"{self._provider} 未配置 API Key")

        self._client = AsyncOpenAI(
            base_url=self._base_url,
            api_key=api_key,
        )

    def _resolve_api_key(self, settings: AppSettings | None, provider: str) -> str | None:
        if settings is None:
            return None
        attr = self._registry.provider_key_map.get(provider, "")
        return getattr(settings, attr, None) if attr else None

    async def stream(
        self,
        messages: list[dict],
        **kwargs: Any,
    ) -> Any:
        try:
            stream = await self._client.chat.completions.create(
                model=self._api_model,
                messages=messages,
                stream=True,
                **kwargs,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            raise ModelAPIError(f"{self._provider} API 调用失败: {e}") from e

    def get_model_name(self) -> str:
        return self._model_name
