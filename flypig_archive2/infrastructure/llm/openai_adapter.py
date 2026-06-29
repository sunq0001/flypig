"""OpenAI/DeepSeek 兼容适配

为什么做：DeepSeek/Qwen/GLM 等国产模型均兼容 OpenAI API 格式，一个适配器可覆盖多数模型。

实现方法：OpenAI SDK stream=True，封装为 IModel 接口的 stream + get_model_name 方法。
构造时接收 model_name，从 model_registry 获取 base_url 和接口模型名，从 Config 获取 API Key。

实现效果：切换国产模型只需改 model_name，适配器自动匹配 base_url。

技术栈：openai SDK, AsyncOpenAI, stream=True

层&依赖：infrastructure.llm 层，实现 IModel，依赖 openai + domain.config
细节见文档：docs/docs_refactor/backend-modules.md → §模型适配、tech-stack.md → §AI 模型 SDK
"""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from domain.config.config import Config
from domain.config.model_registry import REGISTRY
from domain.exceptions import ModelAPIError
from domain.interfaces.imodel import IModel


class OpenAIAdapter(IModel):
    """OpenAI 兼容格式的 LLM 适配器

    适用厂商：DeepSeek / OpenAI / Qwen / GLM / 豆包 / Kimi
    """

    def __init__(self, model_name: str, config: Config | None = None):
        self._model_name = model_name
        self._config = config or Config()

        meta = REGISTRY.get(model_name)
        if not meta:
            raise ModelAPIError(f"未知模型: {model_name}")

        self._provider = meta["provider"]
        self._base_url = meta["base_url"]
        self._api_model = meta["model"]

        is_local = meta.get("local", False)
        if is_local:
            api_key = "not-needed"  # Ollama 不需要 Key
        else:
            api_key = self._config.get_api_key(self._provider)
            if not api_key:
                raise ModelAPIError(f"{self._provider} 未配置 API Key")

        self._client = AsyncOpenAI(
            base_url=self._base_url,
            api_key=api_key,
        )

    async def stream(
        self,
        messages: list[dict],
        **kwargs: Any,
    ) -> Any:
        """逐 token 流式生成回复"""
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
