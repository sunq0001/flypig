"""lifecycle

为什么做：管理应用生命周期事件（启动/关闭），确保资源正确初始化和释放

实现方法：LifecycleEvents 类注册 startup/shutdown 回调，按注册顺序依次触发

层&依赖：bootstrap 层
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from loguru import logger


class LifecycleEvents:
    """生命周期事件注册与触发"""

    def __init__(self):
        self._startup_hooks: list[Callable[[], Coroutine[Any, Any, None]]] = []
        self._shutdown_hooks: list[Callable[[], Coroutine[Any, Any, None]]] = []

    def on_startup(self, fn: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self._startup_hooks.append(fn)

    def on_shutdown(self, fn: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self._shutdown_hooks.append(fn)

    async def fire_startup(self) -> None:
        for fn in self._startup_hooks:
            try:
                await fn()
                logger.info("[lifecycle] startup OK: {}", fn.__name__)
            except Exception as e:
                logger.error("[lifecycle] startup FAILED: {} - {}", fn.__name__, e)

    async def fire_shutdown(self) -> None:
        for fn in reversed(self._shutdown_hooks):
            try:
                await fn()
                logger.info("[lifecycle] shutdown OK: {}", fn.__name__)
            except Exception as e:
                logger.error("[lifecycle] shutdown FAILED: {} - {}", fn.__name__, e)
