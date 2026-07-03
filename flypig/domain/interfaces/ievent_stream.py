"""事件流接口

为什么做：ChatService 需要向前端推送逐 token 事件（token/tool_call/error/done），
但不应直接依赖 SSE 具体实现（sse_queue）。

层&依赖：domain.interfaces 层，depends on nothing
"""

from abc import ABC, abstractmethod


class IEventStream(ABC):
    """事件流接口 — 按 session 隔离推送实时事件"""

    @abstractmethod
    async def push(self, session_id: str, event: str, data: dict) -> None:
        """推送事件到指定会话

        Args:
            session_id: 目标会话 ID
            event: 事件类型 (token / tool_call / error / done)
            data: 事件数据
        """
        ...

    @abstractmethod
    async def pop(self, session_id: str, timeout: float = 30) -> dict | None:
        """从指定会话队列消费事件（阻塞）

        Returns:
            事件字典 {"event": str, "data": dict, "timestamp": str}，超时返回 None
        """
        ...

    @abstractmethod
    def cleanup(self, session_id: str) -> None:
        """清理会话资源"""
        ...
