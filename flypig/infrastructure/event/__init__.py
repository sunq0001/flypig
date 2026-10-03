"""__init__

为什么做：统一导出事件总线实现

实现方法：集中 import + __all__

层&依赖：infrastructure.event 层
"""

from flypig.infrastructure.event.event_bus import InMemoryEventBus

__all__ = [
    "InMemoryEventBus",
]
