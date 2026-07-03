"""ChatApplicationService — 对话应用服务

封装 SSE 流式对话的编排逻辑：接收用户消息 → 创建模型适配器 → 逐 token 流式返回。

层&依赖：application 层，依赖 domain.interfaces
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Optional

from flypig.shared.settings import AppSettings
from flypig.domain.exceptions import ModelAPIError
from flypig.domain.interfaces.imodel_factory import IModelFactory
from flypig.shared.base import ApplicationService


class ChatApplicationService(ApplicationService):
    """对话应用服务 — 编排模型调用与 SSE 事件格式化"""

    def __init__(
        self,
        model_factory: IModelFactory,
        settings: Optional[AppSettings] = None,
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
            yield f"data: {json.dumps({'type': 'error', 'errorText': str(e)})}\n\n"
            return

        try:
            yield f"data: {json.dumps({'type': 'text-start', 'id': 'text-1'})}\n\n"

            async for token in adapter.stream(messages):
                if token:
                    yield f"data: {json.dumps({'type': 'text-delta', 'id': 'text-1', 'delta': token})}\n\n"

            yield f"data: {json.dumps({'type': 'text-end', 'id': 'text-1'})}\n\n"
            yield f"data: {json.dumps({'type': 'finish'})}\n\n"
            yield "data: [DONE]\n\n"
        except ModelAPIError as e:
            yield f"data: {json.dumps({'type': 'error', 'errorText': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'errorText': f'服务错误: {str(e)[:200]}'})}\n\n"
