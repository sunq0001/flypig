"""工作单元接口 — 事务管理

定义事务边界，自动 Commit 或 Rollback，作为仓储的统一入口。
使用 async with uow 上下文管理。

层&依赖：shared.kernel 层，零依赖
"""

from abc import ABC, abstractmethod
from typing import Optional


class UnitOfWork(ABC):
    """工作单元接口 — 事务管理

    职责：
        1. 定义事务边界
        2. 自动 Commit 或 Rollback
        3. 作为仓储的统一入口

    使用方式：
        async with uow:
            await uow.projects.save(project)
            await uow.readpoints.save(readpoint)
            await uow.commit()
    """

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork":
        """进入上下文时开启事务"""
        ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        """退出时：无异常 → commit，有异常 → rollback"""
        ...

    @abstractmethod
    async def commit(self) -> None:
        """提交事务"""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """回滚事务"""
        ...
