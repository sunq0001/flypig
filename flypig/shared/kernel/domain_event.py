"""领域事件基类 — 记录已发生的事实

@dataclass 定义 event_id / occurred_at / aggregate_id。
由 AggregateRoot.record_event 自动填充 aggregate_id。

层&依赖：shared.kernel 层，零依赖
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
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
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_id: str = ""
