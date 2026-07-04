"""对话编排应用服务

为什么做：用户消息进来到 SSE 事件分发出去需要一个编排服务。

实现方法：ChatService 接收用户输入 → 调模型 stream → 将逐 token 事件分发到事件流。
IEventStream 通过构造注入，不依赖具体实现。

层&依赖：orchestration 层，依赖 domain/interfaces
"""

from __future__ import annotations

from flypig.domain.interfaces.ievent_stream import IEventStream
from flypig.domain.interfaces.imodel import IModel


class ChatService:
    """对话编排服务"""

    def __init__(self, model: IModel, event_stream: IEventStream):
        self._model = model
        self._event_stream = event_stream

    async def process_message(self, session_id: str, messages: list[dict]) -> None:
        try:
            async for token in self._model.stream(messages):
                if token:
                    await self._event_stream.push(session_id, "token", {"content": token})

            await self._event_stream.push(session_id, "done", {})
        except Exception as e:
            await self._event_stream.push(session_id, "error", {"message": str(e)[:TRUNCATE_LENGTH]})
