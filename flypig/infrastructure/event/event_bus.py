"""事件总线 — 领域事件路由和派发

为什么做：AggregateRoot.record_event() 记录事件后，需要 EventBus
将事件路由到对应的 Handler。当前只有 EventPublisher 接口定义，缺少实际调度器。

实现方法：InMemoryEventBus 实现 EventPublisher 接口 + 注册/派发能力。
Handler 通过 register() 订阅事件类型，dispatch() 自动匹配并调用。

使用方式：
    bus = InMemoryEventBus()
    bus.register(SessionCreated, SessionCreatedHandler())
    await bus.dispatch(SessionCreated(...))
    # → 自动调用 SessionCreatedHandler.handle(event)

如果未来需要消息队列（RabbitMQ/Redis），只需新建一个实现替换即可。

层&依赖：infrastructure.event 层，依赖 shared.kernel.event_bus + domain.event
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flypig.shared.kernel.domain_event import DomainEvent
from flypig.shared.kernel.event_bus import EventPublisher


class InMemoryEventBus(EventPublisher):
    """内存事件总线 — 同步派发，适合单进程场景

    TODO: 需要引入异步 handler 支持时，替换此实现。
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[DomainEvent], Any]]] = {}

    def register(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], Any],
    ) -> None:
        """注册事件处理器

        Args:
            event_type: 领域事件类（如 SessionCreated）
            handler: 事件处理器回调
        """
        key = event_type.__name__
        if key not in self._handlers:
            self._handlers[key] = []
        self._handlers[key].append(handler)

    async def dispatch(self, event: DomainEvent) -> None:
        """派发单个事件到所有已注册的处理器"""
        key = type(event).__name__
        handlers = self._handlers.get(key, [])
        for handler in handlers:
            await handler.handle(event)  # type: ignore[union-attr]

    # ── EventPublisher 接口实现 ──

    async def publish(self, events: list[DomainEvent]) -> None:
        """批量发布领域事件"""
        for event in events:
            await self.dispatch(event)

    async def publish_one(self, event: DomainEvent) -> None:
        """发布单个领域事件"""
        await self.dispatch(event)
