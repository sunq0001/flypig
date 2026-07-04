"""chat_routes

为什么做：前端 useChat 通过 POST /api/chat 发送用户消息，后端返回 AI SDK v4 SSE 流

实现方法：POST 路由接收 messages + model，调 ChatApplicationService.generate_sse() 返回 text/event-stream 响应

层&依赖：interface.rest.routes 层，通过 ChatApplicationService 依赖 application 层
"""

from __future__ import annotations

from http import HTTPStatus

from quart import Blueprint, current_app, request, Response, jsonify

from flypig.application.chat_service import ChatApplicationService

chat_bp = Blueprint("chat", __name__, url_prefix="/api")


@chat_bp.route("/chat", methods=["POST"])
async def chat():
    data = await request.get_json(force=True) or {}
    messages = data.get("messages", [])
    model_name = data.get("model", "")

    if not messages:
        return jsonify({"error": "messages 不能为空"}), HTTPStatus.BAD_REQUEST
    if not model_name:
        return jsonify({"error": "model 不能为空"}), HTTPStatus.BAD_REQUEST

    service: ChatApplicationService = current_app.config["flypig_chat_service"]

    return Response(
        service.generate_sse(messages, model_name),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
