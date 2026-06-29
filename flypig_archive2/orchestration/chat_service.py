"""对话编排主服务

为什么做：用户消息进来到 SSE 事件分发出去需要一个编排服务，不能直接在路由里写 LangGraph 调用。

实现方法：ChatService 接收用户输入 → 调用 LangGraph StateGraph → 将逐 token 事件分发到 SSE 队列。
R1 阶段为简化版：直接调模型 stream，不经过图。后续轮次接入图。

实现效果：路由层只处理 HTTP 协议，编排逻辑集中在 ChatService 中，测试可 mock。

技术栈：SSE 事件分发, receive → stream → dispatch

层&依赖：orchestration 层，依赖 domain/interfaces（IModel）+ backend/sse_queue
细节见文档：docs/docs_refactor/data-flow.md → §后端数据流、backend-modules.md → §ChatService
"""

from __future__ import annotations

from domain.interfaces.imodel import IModel
from backend.sse_queue import sse_queue


class ChatService:
    """对话编排服务"""

    def __init__(self, model: IModel):
        self._model = model

    async def process_message(self, session_id: str, messages: list[dict]) -> None:
        """处理用户消息，将事件推入 SSE 队列

        Args:
            session_id: 会话 ID
            messages: 完整消息历史（含刚添加的用户消息）
        """
        try:
            async for token in self._model.stream(messages):
                if token:
                    await sse_queue.push(session_id, "token", {"content": token})

            await sse_queue.push(session_id, "done", {})
        except Exception as e:
            await sse_queue.push(session_id, "error", {"message": str(e)[:200]})
