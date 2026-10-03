"""file_events_routes — 文件变化事件 SSE 流

为什么做：让前端通过 EventSource 实时接收工作区文件变化通知，
          后端 FileWatcher（watchdog）将变化推入队列供此路由消费。
实现方法：GET /api/events/files 返回 text/event-stream。
层&依赖：interface.rest.routes 层
"""

from __future__ import annotations

import asyncio
import json
import logging

from quart import Blueprint, Response

from flypig.infrastructure.files.file_watcher import file_event_queue

_log = logging.getLogger(__name__)

file_events_bp = Blueprint("file_events", __name__, url_prefix="/api")


@file_events_bp.route("/events/files", methods=["GET"])
async def sse_file_events() -> Response:
    """文件变化 SSE 流（由 FileWatcher 写入 watchdog 事件）"""

    async def _stream():
        yield "event: connected\ndata:\n\n"
        while True:
            try:
                event_str = await file_event_queue.get()
                action, name = event_str.split(":", 1)
                _log.info("[sse/file] %s: %s", action, name)
                payload = json.dumps({"action": action, "name": name})
                yield f"data: {payload}\n\n"
            except asyncio.CancelledError:
                break
            except Exception as e:
                # 单条事件解析失败不应中断整条流
                _log.warning("[sse/file] 事件处理异常: %s", e)
                continue

    return Response(
        _stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
