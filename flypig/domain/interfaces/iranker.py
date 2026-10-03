"""排序器接口

为什么做：搜索结果/工具建议等需要按相关性排序，不同排序策略通过统一接口切换。

实现方法：IRanker ABC 定义 rank() 方法。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod
from typing import Any


class IRanker(ABC):
    """排序器接口 — 相关性排序"""

    @abstractmethod
    async def rank(self, items: list[Any], query: str) -> list[Any]: ...
