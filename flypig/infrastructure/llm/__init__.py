"""LLM 模型适配包

为什么做：不同 LLM API（DeepSeek/Claude/GPT/本地模型）的调用方式不同，需要统一适配。
实现方法：OpenAI 兼容适配 / Anthropic SDK / Ollama 本地模型，各实现 IModel 接口。

使用方式：
    from flypig.infrastructure.llm import OpenAIAdapter, ModelFactory
"""

from flypig.infrastructure.llm.model_factory import ModelFactory
from flypig.infrastructure.llm.openai_adapter import OpenAIAdapter

__all__ = [
    "ModelFactory",
    "OpenAIAdapter",
]
