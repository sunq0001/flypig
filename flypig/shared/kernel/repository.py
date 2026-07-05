"""Repository — 仓储接口泛型

为什么做：领域层需要持久化聚合根，但不应依赖具体的数据库实现（SQLite、PostgreSQL 等）。
Repository 接口在 domain 层定义，基础设施层负责实现。

实现方法：泛型 ABC，T 限定为 Entity 子类。定义 save / find_by_id / delete / list_all 四个方法。
一个 Repository 只负责一种聚合根的全生命周期管理。

层&依赖：shared.kernel 层，依赖 Entity
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from flypig.shared.kernel.entity import Entity

T = TypeVar("T", bound=Entity)


class Repository(ABC, Generic[T]):
    """仓储接口泛型 — 持久化抽象

    领域层定义接口，基础设施层实现。
    一个 Repository 只负责一种聚合根的全生命周期管理。
    """

    @abstractmethod
    async def save(self, entity: T) -> None:
        """保存实体（新增或更新）"""
        ...

    @abstractmethod
    async def find_by_id(self, id: str) -> T | None:
        """按 ID 查找"""
        ...

    @abstractmethod
    async def delete(self, entity: T) -> None:
        """删除实体"""
        ...

    @abstractmethod
    async def list_all(self) -> list[T]:
        """列出所有"""
        ...
