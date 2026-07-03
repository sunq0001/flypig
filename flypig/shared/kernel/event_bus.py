"""事件发布器接口 — 领域层定义，基础设施层实现

AggregateRoot.pull_events() 取出事件后，由 ApplicationService
调用 EventPublisher.publish() 发出。

层&依赖：shared.kernel 层，依赖 domain_event
"""

from abc import ABC, abstractmethod
from typing import List

from flypig.shared.kernel.domain_event import DomainEvent


class EventPublisher(ABC):
    """事件发布器接口 — 领域层定义，基础设施层实现

    AggregateRoot.pull_events() 取出事件后，由 ApplicationService
    调用 EventPublisher.publish() 发出。
    """

    @abstractmethod
    async def publish(self, events: List[DomainEvent]) -> None:
        """批量发布领域事件到消息中间件"""
        ...

    @abstractmethod
    async def publish_one(self, event: DomainEvent) -> None:
        """发布单个领域事件"""
        ...
