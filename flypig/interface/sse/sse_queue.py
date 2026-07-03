"""SSE 事件队列实现

实现方法：asyncio.Queue 封装，按 session_id 隔离。
实现 IEventStream 接口，供 ChatService 依赖注入。

技术栈：asyncio.Queue, IEventStream
层&依赖：interface 层，实现 domain.interfaces.ievent_stream
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from flypig.domain.interfaces.ievent_stream import IEventStream


class SSEQueue(IEventStream):
    """SSE 事件队列，按 session_id 隔离"""

    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = {}

    def _get_queue(self, session_id: str) -> asyncio.Queue:
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue(maxsize=500)
        return self._queues[session_id]

    async def push(self, session_id: str, event: str, data: dict) -> None:
        queue = self._get_queue(session_id)
        await queue.put({
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def pop(self, session_id: str, timeout: float = 30) -> dict | None:
        queue = self._get_queue(session_id)
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def cleanup(self, session_id: str) -> None:
        self._queues.pop(session_id, None)


# 全局单例
sse_queue = SSEQueue()
