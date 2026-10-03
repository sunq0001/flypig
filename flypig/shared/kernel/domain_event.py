"""DomainEvent — 领域事件基类

为什么做：领域事件记录领域内已发生的事实，用于解耦聚合根之间的通信。
例如"会话已创建"、"消息已发送"等事件由 AggregateRoot 记录，
通过 EventBus 路由到对应的 Handler 处理。

实现方法：@dataclass 定义 event_id / occurred_at / aggregate_id 三个字段。
由 AggregateRoot.record_event 自动填充 aggregate_id。

层&依赖：shared.kernel 层，零依赖
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass
class DomainEvent:
    """领域事件基类 — 记录已发生的事实

    属性：
        event_id: 事件唯一标识
        occurred_at: 事件发生时间（UTC）
        aggregate_id: 所属聚合根 ID（由 AggregateRoot.record_event 自动填充）
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    aggregate_id: str = ""
