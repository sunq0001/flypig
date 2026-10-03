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
from collections.abc import AsyncGenerator, Callable
from typing import Any

from loguru import logger as _log

from flypig.domain.exceptions import ModelAPIError
from flypig.domain.interfaces.imodel_factory import IModelFactory
from flypig.domain.interfaces.itool_executor import IToolExecutor
from flypig.domain.prompts.multirole_manager import MultiRoleManager
from flypig.orchestration.graph_factory import GraphFactory
from flypig.orchestration.tool_event_hub import get_hub
from flypig.shared.base import ApplicationService
from flypig.shared.constants import SSE_EVENT_ERROR as SSE_ERROR
from flypig.shared.constants import SSE_EVENT_FINISH as SSE_FINISH
from flypig.shared.constants import SSE_EVENT_TEXT_DELTA as SSE_TEXT_DELTA
from flypig.shared.constants import SSE_EVENT_TEXT_END as SSE_TEXT_END
from flypig.shared.constants import SSE_EVENT_TEXT_START as SSE_TEXT_START
from flypig.shared.settings import AppSettings

_KEY_TYPE = "type"
_KEY_ERROR_TEXT = "errorText"
_ID_TEXT = "text-1"
_TRUNCATE_LENGTH = 200
_SSE_DONE = "data: [DONE]\n\n"

# 秒：无数据时发心跳保持连接存活 / 等待图任务收尾的超时
_HEARTBEAT_INTERVAL = 10
_GRAPH_DRAIN_TIMEOUT = 5


def _sse_error_event(error_text: str) -> str:
    """构造 error 类型的 SSE data 行"""
    return f"data: {json.dumps({_KEY_TYPE: SSE_ERROR, _KEY_ERROR_TEXT: error_text})}\n\n"


def _build_context_messages(messages: list[dict], settings: AppSettings | None) -> list[dict]:
    """注入 developer 系统 prompt（消息中已有 system 时不重复注入）"""
    ctx_messages = list(messages)
    if any(m.get("role") == "system" for m in ctx_messages):
        return ctx_messages

    role_content = MultiRoleManager().get_system_message("developer")
    workspace = settings.workspace if settings else None
    if workspace:
        role_content += f"\n\n当前工作区目录: {workspace}"
    ctx_messages.insert(0, {"role": "system", "content": role_content})
    return ctx_messages


async def _run_graph(
    graph_factory: GraphFactory,
    messages: list[dict],
    settings: AppSettings | None,
    session_id: str,
    token_queue: asyncio.Queue[str | None],
) -> None:
    """执行会话图，并在结束时投递哨兵（None）唤醒消费端"""
    try:
        await graph_factory.invoke(
            session_id,
            {
                "messages": _build_context_messages(messages, settings),
                "session_id": session_id,
                "mode": "explore",
                "turn_id": 0,
            },
        )
    finally:
        token_queue.put_nowait(None)


async def _wait_graph_task(graph_task: asyncio.Task) -> None:
    """等待图任务收尾（超时/异常只记日志，不改变已推流内容）"""
    try:
        await asyncio.wait_for(graph_task, timeout=_GRAPH_DRAIN_TIMEOUT)
    except TimeoutError:
        _log.warning("[sse] graph_task 超时，强制继续")
    except Exception as e:
        _log.error("[sse] graph_task 等待异常: {}", str(e)[:_TRUNCATE_LENGTH])


def _make_tool_event_publisher(
    session_id: str, tool_hub
) -> Callable[[str, str, dict, str | None], None]:
    """构造工具事件发布器（把工具调用事件写入 ToolEventHub）"""

    def on_tool_event(phase: str, name: str, args: dict, result: str | None) -> None:
        tool_hub.publish(
            session_id,
            {
                "phase": phase,
                "name": name,
                "args": args,
                "result": result,
            },
        )

    return on_tool_event


async def _drain_token_queue(
    token_queue: asyncio.Queue[str | None],
) -> AsyncGenerator[str, None]:
    """消费 token 队列：超时发心跳，token 发 text-delta，收到哨兵结束"""
    while True:
        try:
            token = await asyncio.wait_for(token_queue.get(), timeout=_HEARTBEAT_INTERVAL)
        except TimeoutError:
            yield ": ping\n\n"
            continue
        if token is None:
            return
        if token:
            yield (
                f"data: {json.dumps({_KEY_TYPE: SSE_TEXT_DELTA, 'id': _ID_TEXT, 'delta': token})}\n\n"
            )


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
        _log.info(
            "[sse] 请求开始 (model={}, session={}, messages={})",
            model_name,
            session_id,
            len(messages),
        )

        try:
            adapter = self._factory.create(model_name, self._settings)
        except ModelAPIError as e:
            _log.error("[sse] 创建模型适配器失败: {}", str(e)[:_TRUNCATE_LENGTH])
            yield _sse_error_event(str(e))
            yield _SSE_DONE
            return

        async for sse in self._stream_with_adapter(adapter, messages, session_id, t_start):
            yield sse

    async def _stream_with_adapter(
        self,
        adapter: Any,
        messages: list[dict],
        session_id: str,
        t_start: float,
    ) -> AsyncGenerator[str, None]:
        """用队列桥接 on_token 回调与图执行，产出完整 SSE 事件序列"""
        token_queue: asyncio.Queue[str | None] = asyncio.Queue()

        def on_token(token: str) -> None:
            token_queue.put_nowait(token)

        # 工具事件 → ToolEventHub（前端独立 SSE 通道消费）
        graph_factory = GraphFactory(
            adapter,
            tool_executor=self._tool_executor,
            on_token=on_token,
            on_tool_event=_make_tool_event_publisher(session_id, get_hub()),
        )

        try:
            yield f"data: {json.dumps({_KEY_TYPE: SSE_TEXT_START, 'id': _ID_TEXT})}\n\n"

            graph_task = asyncio.create_task(
                _run_graph(graph_factory, messages, self._settings, session_id, token_queue)
            )

            async for sse in _drain_token_queue(token_queue):
                yield sse

            await _wait_graph_task(graph_task)

            _log.info("[sse] 请求完成 (耗时={:.2f}s)", time.monotonic() - t_start)
            yield f"data: {json.dumps({_KEY_TYPE: SSE_TEXT_END, 'id': _ID_TEXT})}\n\n"
            yield f"data: {json.dumps({_KEY_TYPE: SSE_FINISH})}\n\n"
            yield _SSE_DONE
        except ModelAPIError as e:
            _log.error("[sse] 模型 API 错误: {}", str(e)[:_TRUNCATE_LENGTH])
            yield _sse_error_event(str(e))
            yield _SSE_DONE
        except Exception as e:
            _log.error("[sse] 服务错误: {}", str(e)[:_TRUNCATE_LENGTH])
            yield _sse_error_event(f"服务错误: {str(e)[:_TRUNCATE_LENGTH]}")
            yield _SSE_DONE
