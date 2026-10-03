"""ToolEventHub — 工具调用事件的会话级发布/订阅

为什么做：tool_call / tool_result 事件需要实时推给前端，但不能污染 /api/chat 的
        ai-sdk SSE 协议流（否则破坏打字机效果）。因此走一条独立的 SSE 通道
        /api/chat/tool-events，由本 hub 在会话内桥接 exec_node 的回调与 SSE 路由。

实现方法：每个 session 一个 asyncio.Queue，exec_node 通过 on_tool_event 回调 publish，
        独立 SSE 路由 drain 该队列。generate_sse 结束时 end() 放哨兵、remove() 清理。

层&依赖：orchestration 层（被 chat_service 与 interface.rest.routes 共享），
        零外部依赖，仅标准库 asyncio + loguru。
"""

from __future__ import annotations

from asyncio import Queue
from typing import Any


class ToolEventHub:
    """会话级工具事件总线"""

    def __init__(self) -> None:
        self._queues: dict[str, Queue] = {}

    def get_or_create(self, session_id: str) -> Queue:
        """获取（或创建）会话对应的事件队列"""
        if session_id not in self._queues:
            self._queues[session_id] = Queue()
        return self._queues[session_id]

    def publish(self, session_id: str, event: dict[str, Any]) -> None:
        """发布一个工具事件（在事件循环内调用，put_nowait 安全）"""
        q = self._queues.get(session_id)
        if q is not None:
            q.put_nowait(event)

    def end(self, session_id: str) -> None:
        """放入哨兵（None），通知 SSE 路由结束"""
        q = self._queues.get(session_id)
        if q is not None:
            q.put_nowait(None)

    def remove(self, session_id: str) -> None:
        """清理会话队列"""
        self._queues.pop(session_id, None)


_hub: ToolEventHub | None = None


def get_hub() -> ToolEventHub:
    """获取全局单例 hub（模块级单例，契合现有 terminal 全局字典风格）"""
    global _hub
    if _hub is None:
        _hub = ToolEventHub()
    return _hub
