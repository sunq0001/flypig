"""仓库接口（预留）

为什么做：领域对象的持久化需要统一的 Repository 模式。

实现方法：Repository ABC，预留待实现。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod
from typing import Any


class Repository(ABC):
    """领域仓库接口 — 统一的持久化入口"""

    @abstractmethod
    async def save(self, entity: Any) -> None: ...

    @abstractmethod
    async def find_by_id(self, entity_id: str) -> Any | None: ...
