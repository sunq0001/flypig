"""应用生命周期事件

为什么做：启动时需要初始化资源（数据库连接、MCP 服务器），关闭时需要清理（关闭线程池、保存状态），
需要一个标准事件机制串联，模块各自注册自己的回调，不侵入 __main__.py。

实现方法：提供 before_server_start / after_server_stop 等 hook 调用点，
模块通过 register_startup / register_shutdown 注册自己的初始化/清理函数。

实现效果：模块可以独立注册生命周期逻辑，新增模块只需在核心装配链路中加一行注册。

技术栈：asyncio, Signal/Event bus

层&依赖：core 层，依赖 logging
细节见文档：docs/docs_refactor/resilience.md → §启动恢复流程
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from loguru import logger


class LifecycleEvents:
    """生命周期事件注册与触发

    使用示例:
        events = LifecycleEvents()
        events.on_startup(my_db_init)
        events.on_shutdown(my_db_close)
        await events.fire_startup()
    """

    def __init__(self):
        self._startup_hooks: list[Callable[[], Coroutine[Any, Any, None]]] = []
        self._shutdown_hooks: list[Callable[[], Coroutine[Any, Any, None]]] = []

    def on_startup(self, fn: Callable[[], Coroutine[Any, Any, None]]) -> None:
        """注册启动时回调"""
        self._startup_hooks.append(fn)

    def on_shutdown(self, fn: Callable[[], Coroutine[Any, Any, None]]) -> None:
        """注册关闭时回调"""
        self._shutdown_hooks.append(fn)

    async def fire_startup(self) -> None:
        """触发所有启动回调"""
        for fn in self._startup_hooks:
            try:
                await fn()
                logger.info("[lifecycle] startup OK: {}", fn.__name__)
            except Exception as e:
                logger.error("[lifecycle] startup FAILED: {} - {}", fn.__name__, e)

    async def fire_shutdown(self) -> None:
        """触发所有关闭回调"""
        for fn in reversed(self._shutdown_hooks):
            try:
                await fn()
                logger.info("[lifecycle] shutdown OK: {}", fn.__name__)
            except Exception as e:
                logger.error("[lifecycle] shutdown FAILED: {} - {}", fn.__name__, e)
