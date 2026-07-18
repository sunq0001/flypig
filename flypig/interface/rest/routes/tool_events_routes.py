"""tool_events_routes

为什么做：工具调用过程（tool_call / tool_result）需要实时推给前端，
        但不能混入 /api/chat 的 ai-sdk 协议流（会破坏打字机）。
        因此单独开一条 SSE：前端在发送消息时额外开一个 EventSource 连本端点，
        按 arrival 顺序渲染工具卡片。

实现方法：GET /api/chat/tool-events?session=<id> 从 ToolEventHub 取该会话队列，
        逐个事件 yield SSE，收到哨兵(None)即结束。

层&依赖：interface.rest.routes 层，依赖 orchestration.tool_event_hub
"""

from __future__ import annotations

import json

from quart import Blueprint, Response, request

from flypig.orchestration.tool_event_hub import get_hub
from flypig.shared.constants import SSE_EVENT_TOOL_CALL, SSE_EVENT_TOOL_RESULT

tool_events_bp = Blueprint("tool_events", __name__, url_prefix="/api")


@tool_events_bp.route("/chat/tool-events", methods=["GET"])
async def chat_tool_events() -> Response:
    """工具事件 SSE 流（与 /api/chat 的 ai-sdk 文本流物理隔离）"""
    session_id = request.args.get("session", "default")
    hub = get_hub()
    q = hub.get_or_create(session_id)

    async def generate():
        while True:
            event = await q.get()
            if event is None:
                yield "data: [DONE]\n\n"
                break
            if event.get("phase") == "call":
                payload = {
                    "type": SSE_EVENT_TOOL_CALL,
                    "name": event.get("name", ""),
                    "args": event.get("args", {}),
                }
            elif event.get("phase") == "result":
                payload = {
                    "type": SSE_EVENT_TOOL_RESULT,
                    "name": event.get("name", ""),
                    "args": event.get("args", {}),
                    "result": event.get("result", ""),
                }
            else:
                continue
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
