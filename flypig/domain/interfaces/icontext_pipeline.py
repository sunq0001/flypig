"""上下文流水线接口

为什么做：对话上下文需要经过多步处理（截断/压缩/格式化/注入系统 prompt），用流水线模式串联。

实现方法：IContextPipeline ABC 定义 process() 方法。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod
from typing import Any


class IContextPipeline(ABC):
    """上下文流水线接口 — 多步处理对话上下文"""

    @abstractmethod
    async def process(self, messages: list[dict], context: dict[str, Any]) -> list[dict]: ...
