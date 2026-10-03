"""SqliteUnitOfWork — SQLite 事务边界实现

为什么做：shared.kernel 定义了 UnitOfWork 接口（一个业务操作跨多个仓储写入时
         需要原子性），但项目里一直没有任何实现，事务边界形同虚设。
         先落地一个语义正确的最小实现，供后续 sqlite 仓储复用。
实现方法：基于标准库 sqlite3，进入上下文时 BEGIN，退出时无异常 → commit、
         有异常 → rollback；commit/rollback 通过 asyncio.to_thread 执行，
         避免阻塞事件循环。
层&依赖：infrastructure.persistence 层，实现 shared.kernel.unit_of_work.UnitOfWork
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from loguru import logger as _log

from flypig.shared.kernel.unit_of_work import UnitOfWork

# 默认数据库（内存库，便于测试与无状态使用）
DEFAULT_DB_PATH = ":memory:"


class SqliteUnitOfWork(UnitOfWork):
    """基于 sqlite3 的工作单元（事务边界）

    使用方式：
        async with SqliteUnitOfWork(db_path) as uow:
            uow.connection.execute("INSERT ...")
            await uow.commit()
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    @property
    def connection(self) -> sqlite3.Connection | None:
        """当前事务使用的连接（未进入上下文时为 None）"""
        return self._conn

    def _open(self) -> sqlite3.Connection:
        """打开连接并开启事务（同步，供线程池调用）"""
        conn = sqlite3.connect(self._db_path)
        conn.isolation_level = None  # 由本类手动控制 BEGIN/COMMIT
        conn.execute("BEGIN")
        return conn

    async def __aenter__(self) -> SqliteUnitOfWork:
        try:
            self._conn = await asyncio.to_thread(self._open)
        except Exception as e:
            _log.error("[uow] 打开数据库失败: {}", e)
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        try:
            if exc_type is None:
                await self.commit()
            else:
                await self.rollback()
        finally:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    async def commit(self) -> None:
        """提交事务"""
        if self._conn is None:
            return
        try:
            await asyncio.to_thread(self._conn.commit)
        except Exception as e:
            _log.error("[uow] 提交事务失败: {}", e)
            raise

    async def rollback(self) -> None:
        """回滚事务"""
        if self._conn is None:
            return
        try:
            await asyncio.to_thread(self._conn.rollback)
        except Exception as e:
            _log.error("[uow] 回滚事务失败: {}", e)
            raise


__all__ = ["DEFAULT_DB_PATH", "SqliteUnitOfWork"]
