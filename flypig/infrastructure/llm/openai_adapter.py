"""openai_adapter

为什么做：OpenAI 兼容格式的 LLM API（DeepSeek/Qwen/GLM/豆包等）需要统一适配器

实现方法：封装 AsyncOpenAI SDK，stream 方法返回异步 token 生成器。配置来自 model_registry.json + AppSettings

层&依赖：infrastructure.llm 层，实现 domain.interfaces.imodel
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI

from flypig.domain.exceptions import ModelAPIError
from flypig.domain.interfaces.chat_chunk import ChatChunk
from flypig.domain.interfaces.imodel import IModel
from flypig.domain.registry import ModelRegistry
from flypig.shared.settings import AppSettings


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
    ) -> AsyncGenerator[str, None]:
        try:
            stream = await self._client.chat.completions.create(  # pyright: ignore[reportCallIssue,reportArgumentType]
                model=self._api_model,
                messages=messages,  # pyright: ignore[reportArgumentType]
                stream=True,
                **kwargs,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            raise ModelAPIError(f"{self._provider} API 调用失败: {e}") from e

    async def stream_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        **kwargs: Any,
    ) -> AsyncGenerator[ChatChunk, None]:
        """带工具调用的流式生成

        OpenAI streaming function calling 的 chunk 结构：
        - 普通回答：delta.content 逐 token 产出
        - 工具调用：delta.tool_calls 分片到达，需按 index 累积后解析 arguments JSON
        - 流末尾：最后一块 chunk 通常会标记 finish_reason="tool_calls"
        """
        try:
            stream = await self._client.chat.completions.create(  # pyright: ignore[reportCallIssue,reportArgumentType]
                model=self._api_model,
                messages=messages,  # pyright: ignore[reportArgumentType]
                tools=tools,  # pyright: ignore[reportArgumentType]
                stream=True,
                **kwargs,
            )

            tool_calls_acc: dict[int, dict[str, Any]] = {}
            has_tool_calls = False

            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                # 文本 token
                if delta.content:
                    yield ChatChunk(text=delta.content)

                # 工具调用分片（按 index 累积）
                if delta.tool_calls:
                    has_tool_calls = True
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "_id": "",
                                "_name": "",
                                "_args_str": "",
                            }
                        if tc_delta.id:
                            tool_calls_acc[idx]["_id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tool_calls_acc[idx]["_name"] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_calls_acc[idx]["_args_str"] += tc_delta.function.arguments

            # 流结束，产出 tool_calls
            if has_tool_calls:
                final_tool_calls = []
                for idx in sorted(tool_calls_acc.keys()):
                    acc = tool_calls_acc[idx]
                    args_str = acc["_args_str"] or "{}"
                    try:
                        parsed_args = json.loads(args_str)
                    except json.JSONDecodeError:
                        parsed_args = {"_raw": args_str}
                    final_tool_calls.append(
                        {
                            "id": acc["_id"],
                            "name": acc["_name"],
                            "arguments": parsed_args,
                        }
                    )
                yield ChatChunk(tool_calls=final_tool_calls)

        except Exception as e:
            raise ModelAPIError(f"{self._provider} API 调用失败: {e}") from e

    def get_model_name(self) -> str:
        return self._model_name
