"""chat_service

为什么做：封装 SSE 流式对话的编排逻辑：接收用户消息 → 创建模型适配器 → 逐 token 流式返回

实现方法：ChatApplicationService 通过 IModelFactory 创建适配器，调 adapter.stream() 得到 token 流，格式化为 SSE 事件字符串返回

层&依赖：application 层，依赖 domain.interfaces
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from flypig.domain.exceptions import ModelAPIError
from flypig.domain.interfaces.imodel_factory import IModelFactory
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


class ChatApplicationService(ApplicationService):
    """对话应用服务 — 编排模型调用与 SSE 事件格式化"""

    def __init__(
        self,
        model_factory: IModelFactory,
        settings: AppSettings | None = None,
    ) -> None:
        self._factory = model_factory
        self._settings = settings

    async def generate_sse(
        self,
        messages: list[dict],
        model_name: str,
    ) -> AsyncGenerator[str, None]:
        """生成 SSE 格式的流式响应

        Args:
            messages: 对话消息列表
            model_name: 模型名

        Yields:
            SSE 格式字符串（text-start / text-delta / text-end / finish / error）
        """
        try:
            adapter = self._factory.create(model_name, self._settings)
        except ModelAPIError as e:
            yield f"data: {json.dumps({'type': SSE_ERROR, 'errorText': str(e)})}\n\n"
            return

        try:
            yield f"data: {json.dumps({_KEY_TYPE: SSE_TEXT_START, 'id': _ID_TEXT})}\n\n"

            async for token in adapter.stream(messages):
                if token:
                    yield f"data: {json.dumps({_KEY_TYPE: SSE_TEXT_DELTA, 'id': _ID_TEXT, 'delta': token})}\n\n"

            yield f"data: {json.dumps({_KEY_TYPE: SSE_TEXT_END, 'id': _ID_TEXT})}\n\n"
            yield f"data: {json.dumps({_KEY_TYPE: SSE_FINISH})}\n\n"
            yield "data: [DONE]\n\n"
        except ModelAPIError as e:
            yield f"data: {json.dumps({_KEY_TYPE: SSE_ERROR, 'errorText': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({_KEY_TYPE: SSE_ERROR, 'errorText': f'服务错误: {str(e)[:TRUNCATE_LENGTH]}'})}\n\n"
