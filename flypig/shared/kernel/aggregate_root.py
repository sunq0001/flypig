"""聚合根基类 — 管理内部实体一致性和领域事件

约束：一个事务只修改一个聚合根实例。通过 record_event 记录事件，
pull_events 取出事件后由 ApplicationService 通过 EventPublisher 发布。

层&依赖：shared.kernel 层，依赖 entity + domain_event
"""

from typing import List

from flypig.shared.kernel.domain_event import DomainEvent
from flypig.shared.kernel.entity import Entity


class AggregateRoot(Entity):
    """聚合根基类 — 管理内部实体一致性和领域事件

    约束：
        1. 一个事务只修改一个聚合根实例
        2. 聚合根通过 record_event 记录事件，通过 pull_events 取出发布
        3. 外部只能通过聚合根的方法修改内部状态
    """

    def __init__(self, id: str = "") -> None:
        super().__init__(id)
        self._events: List[DomainEvent] = []

    def record_event(self, event: DomainEvent) -> None:
        """记录一个领域事件（暂存于内存，等待发布）"""
        event.aggregate_id = self.id
        self._events.append(event)

    def pull_events(self) -> List[DomainEvent]:
        """拉取并清空已记录的所有领域事件"""
        events = list(self._events)
        self._events.clear()
        return events
