"""UnitOfWork — 工作单元接口

为什么做：一个业务操作可能涉及多个 Repository 的写入，需要事务保证原子性。
UnitOfWork 定义了事务边界：全部成功则 commit，任一失败则 rollback。

实现方法：async context manager（__aenter__ / __aexit__），
退出时无异常 → commit，有异常 → rollback。

层&依赖：shared.kernel 层，零依赖
"""

from abc import ABC, abstractmethod


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
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
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
