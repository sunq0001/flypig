"""缓存接口

为什么做：AI 响应缓存/上下文缓存需要统一存储入口，支持内存/Redis/文件多种后端切换。

实现方法：ICache ABC 定义 get/set/delete/clear 方法，基础设施层实现具体后端。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod
from typing import Any


class ICache(ABC):
    """缓存接口 — 统一 get/set/delete/clear"""

    @abstractmethod
    async def get(self, key: str) -> Any | None: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def clear(self) -> None: ...
