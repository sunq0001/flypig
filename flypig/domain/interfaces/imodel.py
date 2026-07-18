"""LLM 模型适配接口

为什么做：不同 LLM API（DeepSeek/Claude/GPT、国产模型）的调用方式不同，需要统一接口屏蔽差异。

实现方法：IModel ABC 定义 stream 方法（逐 token 流式生成）和 get_model_name 方法，各模型适配器分别实现。
OpenAI 兼容路径（DeepSeek/Qwen/GLM/豆包）统一走 openai_adapter.py，Anthropic 走 anthropic.py。

实现效果：改模型只需换适配器，对话编排代码不变。chat_node 只调 model.stream(messages)。

技术栈：ABC, @abstractmethod, async generator

层&依赖：domain.interfaces 层，依赖 domain/exceptions.py（ModelAPIError）
细节见文档：docs/docs_refactor/backend-modules.md → §模型适配、langgraph-graph.md → §chat 节点
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from flypig.domain.interfaces.chat_chunk import ChatChunk


class IModel(ABC):
    """LLM 模型适配接口"""

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """逐 token 流式生成回复

        Args:
            messages: 对话消息列表 [{"role": "user"/"assistant", "content": "..."}, ...]
            **kwargs: 额外参数（temperature / max_tokens / stream_options 等）

        Yields:
            每个 token 的文本片段，由 chat_service 逐片推 SSE

        Raises:
            ModelAPIError: API 认证失败、限流、服务不可用
        """
        ...

    @abstractmethod
    async def stream_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        **kwargs,
    ) -> AsyncGenerator[ChatChunk, None]:
        """带工具调用的流式生成

        当 LLM 决定调用工具时，流的末尾会产出一个带有 tool_calls 的 ChatChunk；
        当 LLM 选择直接回答时，逐 token 产出 text ChatChunk。

        Args:
            messages: 对话消息列表
            tools: OpenAI function calling 格式的工具 schema 列表
            **kwargs: 额外参数（temperature / max_tokens 等）

        Yields:
            ChatChunk，可能含 text 或 tool_calls（或两者同时）

        Raises:
            ModelAPIError: API 认证失败、限流、服务不可用
        """
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """返回当前模型名（如 deepseek-v4-flash），用于日志和用量追踪"""
        ...
