"""对话编排应用服务

为什么做：用户消息进来到 SSE 事件分发出去需要一个编排服务。

实现方法：ChatService 接收用户输入 → 调模型 stream → 将逐 token 事件分发到 SSE 队列。
R1 阶段为简化版：直接调模型 stream。后续轮次接入 LangGraph。

层&amp;依赖：application 层，依赖 domain/interfaces + interface/sse
"""

from __future__ import annotations

from flypig.domain.interfaces.imodel import IModel
from flypig.interface.sse.sse_queue import sse_queue


class ChatService:
    """对话编排服务"""

    def __init__(self, model: IModel):
        self._model = model

    async def process_message(self, session_id: str, messages: list[dict]) -> None:
        try:
            async for token in self._model.stream(messages):
                if token:
                    await sse_queue.push(session_id, "token", {"content": token})

            await sse_queue.push(session_id, "done", {})
        except Exception as e:
            await sse_queue.push(session_id, "error", {"message": str(e)[:200]})
