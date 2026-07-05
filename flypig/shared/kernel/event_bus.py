"""EventPublisher — 事件发布器接口

为什么做：AggregateRoot.pull_events() 取出的领域事件需要发布到消息中间件
或事件总线，由对应的 Handler 处理。领域层只定义接口，不负责实现。

实现方法：ABC + @abstractmethod 定义 publish / publish_one 两个方法。
基础设施层（如 InfMemoryEventBus）负责具体实现。

层&依赖：shared.kernel 层，依赖 DomainEvent
"""

from abc import ABC, abstractmethod

from flypig.shared.kernel.domain_event import DomainEvent


class EventPublisher(ABC):
    """事件发布器接口 — 领域层定义，基础设施层实现

    AggregateRoot.pull_events() 取出事件后，由 ApplicationService
    调用 EventPublisher.publish() 发出。
    """

    @abstractmethod
    async def publish(self, events: list[DomainEvent]) -> None:
        """批量发布领域事件到消息中间件"""
        ...

    @abstractmethod
    async def publish_one(self, event: DomainEvent) -> None:
        """发布单个领域事件"""
        ...
