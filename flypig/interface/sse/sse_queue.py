"""sse_queue

为什么做：ChatService 需要按 session 隔离推送实时事件，IEventStream 接口的 asyncio.Queue 实现

实现方法：SSEQueue 实现 IEventStream 接口，内部用 dict[str, asyncio.Queue] 按 session_id 隔离

层&依赖：interface.sse 层，实现 domain.interfaces.ievent_stream
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from flypig.domain.interfaces.ievent_stream import IEventStream
from flypig.shared.constants import MAX_QUEUE_SIZE


class SSEQueue(IEventStream):
    """SSE 事件队列，按 session_id 隔离"""

    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = {}

    def _get_queue(self, session_id: str) -> asyncio.Queue:
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        return self._queues[session_id]

    async def push(self, session_id: str, event: str, data: dict) -> None:
        queue = self._get_queue(session_id)
        await queue.put(
            {
                "event": event,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    async def pop(self, session_id: str, timeout: float = POP_TIMEOUT) -> dict | None:
        queue = self._get_queue(session_id)
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except TimeoutError:
            return None

    def cleanup(self, session_id: str) -> None:
        self._queues.pop(session_id, None)


# 全局单例
sse_queue = SSEQueue()
