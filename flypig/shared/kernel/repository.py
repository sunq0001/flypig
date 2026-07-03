"""仓储接口泛型 — 持久化抽象

领域层定义接口，基础设施层实现。一个 Repository 只负责一种聚合根的全生命周期管理。

层&依赖：shared.kernel 层，依赖 entity
"""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

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
    async def find_by_id(self, id: str) -> Optional[T]:
        """按 ID 查找"""
        ...

    @abstractmethod
    async def delete(self, entity: T) -> None:
        """删除实体"""
        ...

    @abstractmethod
    async def list_all(self) -> List[T]:
        """列出所有"""
        ...
