"""SSE 队列抽象

为什么做：LangGraph 的事件需要异步推送到前端 SSE 连接，需要一个线程安全的队列抽象。

实现方法：asyncio.Queue 封装，event_queue 存放事件，events_for_session 按 session_id 隔离。
ChatService 推事件，SSE 端点轮询消费。

实现效果：事件推送不阻塞 LangGraph 执行，前端实时接收流式事件。

技术栈：asyncio.Queue, 按 session_id 隔离

层&依赖：backend 层，依赖 asyncio
细节见文档：docs/docs_refactor/data-flow.md → §SSE 事件流
"""

from __future__ import annotations

import asyncio
from datetime import datetime


class SSEQueue:
    """SSE 事件队列，按 session_id 隔离"""

    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = {}

    def _get_queue(self, session_id: str) -> asyncio.Queue:
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue(maxsize=500)
        return self._queues[session_id]

    async def push(self, session_id: str, event: str, data: dict) -> None:
        """推送事件到指定会话的队列

        Args:
            session_id: 目标会话
            event: 事件类型 (token / tool_call / error / done)
            data: 事件数据
        """
        queue = self._get_queue(session_id)
        await queue.put({
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def pop(self, session_id: str, timeout: float = 30) -> dict | None:
        """从指定会话队列消费事件（阻塞）"""
        queue = self._get_queue(session_id)
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def cleanup(self, session_id: str) -> None:
        """清理会话队列"""
        self._queues.pop(session_id, None)


# 全局单例
sse_queue = SSEQueue()
