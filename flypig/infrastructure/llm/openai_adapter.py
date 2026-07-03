"""OpenAI/DeepSeek 兼容适配

配置数据（如本地模型名、API路径前缀等）来自 model_registry.json。
"""

from __future__ import annotations

from typing import Any, Optional

from openai import AsyncOpenAI

from flypig.domain.exceptions import ModelAPIError
from flypig.domain.model_ref import REGISTRY, PROVIDER_KEY_MAP, get_local_config
from flypig.bootstrap.settings import AppSettings
from flypig.domain.interfaces.imodel import IModel


class OpenAIAdapter(IModel):
    """OpenAI 兼容格式的 LLM 适配器"""

    def __init__(self, model_name: str, settings: Optional[AppSettings] = None):
        self._model_name = model_name

        meta = REGISTRY.get(model_name)
        if meta:
            self._provider = meta["provider"]
            self._base_url = meta["base_url"]
            self._api_model = meta["api_model"]
            is_local = meta.get("local", False)
        else:
            local = get_local_config()
            self._provider = local.get("provider", "Local")
            api_path = local.get("api_path", "/v1")
            base_url = settings.ollama_base_url or local.get("default_ollama_url", "")
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

    @staticmethod
    def _resolve_api_key(settings: Optional[AppSettings], provider: str) -> Optional[str]:
        if settings is None:
            return None
        attr = PROVIDER_KEY_MAP.get(provider, "")
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
