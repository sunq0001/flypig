"""LifecycleEvents — 应用生命周期事件

为什么做：启动时需要初始化资源，关闭时需要清理（关闭线程池、保存状态），
需要一个标准事件机制串联，模块各自注册自己的回调。

实现方法：提供 on_startup / on_shutdown 注册，fire_startup / fire_shutdown 依次触发。

实现效果：模块独立注册生命周期逻辑，新增模块只需在核心装配链路中加一行注册。

层&amp;依赖：bootstrap 层，依赖 logging
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
