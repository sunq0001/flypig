"""搜索接口

为什么做：代码搜索/文档搜索/网络搜索需要统一入口，搜索后端可切换。

实现方法：ISearch ABC 定义 search() 方法。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod
from typing import Any


class ISearch(ABC):
    """搜索接口 — 统一搜索入口"""

    @abstractmethod
    async def search(self, query: str, source: str = "web") -> list[dict[str, Any]]: ...
