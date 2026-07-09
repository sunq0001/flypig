"""chat_service

为什么做：通过 LangGraph 编排对话流程：接收用户消息 → 创建图谱 → 节点流式推 SSE → 返回完整状态。

实现方法：ChatApplicationService 创建模型适配器 → GraphFactory → invoke() →
         chat_node 通过 on_token 回调实时推 SSE token → 完成后 yield finish 事件。

层&依赖：orchestration 层，依赖 domain.interfaces + orchestration.graph_factory
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator

from loguru import logger as _log

from flypig.domain.exceptions import ModelAPIError
from flypig.domain.interfaces.imodel_factory import IModelFactory
from flypig.domain.interfaces.itool_executor import IToolExecutor
from flypig.orchestration.graph_factory import GraphFactory
from flypig.shared.base import ApplicationService
from flypig.shared.constants import (
    SSE_EVENT_ERROR as SSE_ERROR,
)
from flypig.shared.constants import (
    SSE_EVENT_FINISH as SSE_FINISH,
)
from flypig.shared.constants import (
    SSE_EVENT_TEXT_DELTA as SSE_TEXT_DELTA,
)
from flypig.shared.constants import (
    SSE_EVENT_TEXT_END as SSE_TEXT_END,
)
from flypig.shared.constants import (
    SSE_EVENT_TEXT_START as SSE_TEXT_START,
)
from flypig.shared.settings import AppSettings

_KEY_TYPE = "type"
_ID_TEXT = "text-1"
_TRUNCATE_LENGTH = 200


class ChatApplicationService(ApplicationService):
    """对话应用服务 — 通过 LangGraph 编排对话与 SSE 实时推流"""

    def __init__(
        self,
        model_factory: IModelFactory,
        tool_executor: IToolExecutor | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self._factory = model_factory
        self._tool_executor = tool_executor
        self._settings = settings

    async def generate_sse(
        self,
        messages: list[dict],
        model_name: str,
        session_id: str = "default",
    ) -> AsyncGenerator[str, None]:
        """通过 LangGraph 生成 SSE 格式的流式响应

        Args:
            messages: 对话消息列表
            model_name: 模型名
            session_id: 会话 ID

        Yields:
            SSE 格式字符串（text-start / text-delta / text-end / finish / error）
        """
        t_start = time.monotonic()
        _log.info("[sse] 请求开始 (model={}, session={}, messages={})", model_name, session_id, len(messages))

        try:
            adapter = self._factory.create(model_name, self._settings)
        except ModelAPIError as e:
            _log.error("[sse] 创建模型适配器失败: {}", str(e)[:200])
            yield f"data: {json.dumps({_KEY_TYPE: SSE_ERROR, 'errorText': str(e)})}\n\n"
            return

        # 用队列桥接 on_token 回调 → SSE yield
        token_queue: asyncio.Queue[str | None] = asyncio.Queue()

        def on_token(token: str) -> None:
            token_queue.put_nowait(token)

        graph_factory = GraphFactory(adapter, tool_executor=self._tool_executor, on_token=on_token)

        try:
            yield f"data: {json.dumps({_KEY_TYPE: SSE_TEXT_START, 'id': _ID_TEXT})}\n\n"

            async def run_graph() -> None:
                try:
                    await graph_factory.invoke(
                        session_id,
                        {
                            "messages": messages,
                            "session_id": session_id,
                            "mode": "explore",
                            "turn_id": 0,
                        },
                    )
                finally:
                    token_queue.put_nowait(None)  # 哨兵：结束

            graph_task = asyncio.create_task(run_graph())

            while True:
                token = await token_queue.get()
                if token is None:
                    break
                if token:
                    yield (
                        f"data: {json.dumps({_KEY_TYPE: SSE_TEXT_DELTA, 'id': _ID_TEXT, 'delta': token})}\n\n"
                    )

            await graph_task

            elapsed = time.monotonic() - t_start
            _log.info("[sse] 请求完成 (耗时={:.2f}s)", elapsed)

            yield f"data: {json.dumps({_KEY_TYPE: SSE_TEXT_END, 'id': _ID_TEXT})}\n\n"
            yield f"data: {json.dumps({_KEY_TYPE: SSE_FINISH})}\n\n"
            yield "data: [DONE]\n\n"
        except ModelAPIError as e:
            _log.error("[sse] 模型 API 错误: {}", str(e)[:200])
            yield f"data: {json.dumps({_KEY_TYPE: SSE_ERROR, 'errorText': str(e)})}\n\n"
        except Exception as e:
            _log.error("[sse] 服务错误: {}", str(e)[:_TRUNCATE_LENGTH])
            yield f"data: {json.dumps({_KEY_TYPE: SSE_ERROR, 'errorText': f'服务错误: {str(e)[:_TRUNCATE_LENGTH]}'})}\n\n"
