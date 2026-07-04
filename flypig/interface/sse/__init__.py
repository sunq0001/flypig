"""__init__

为什么做：统一导出 SSE 事件流接口实现

实现方法：集中 import + __all__

层&依赖：interface.sse 层
"""

from flypig.interface.sse.sse_queue import SSEQueue, sse_queue

__all__ = [
    "SSEQueue",
    "sse_queue",
]
