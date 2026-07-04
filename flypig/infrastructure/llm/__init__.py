"""__init__

为什么做：不同 LLM API 的适配器统一出口

实现方法：集中 import + __all__

层&依赖：infrastructure.llm 层
"""

from flypig.infrastructure.llm.model_factory import ModelFactory
from flypig.infrastructure.llm.openai_adapter import OpenAIAdapter

__all__ = [
    "ModelFactory",
    "OpenAIAdapter",
]
