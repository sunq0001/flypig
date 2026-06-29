"""SSE 聊天路由 (/api/chat)

为什么做：前端 useChat 通过 POST /api/chat 发送用户消息，后端返回 AI SDK v4 SSE 流。

层&amp;依赖：interface.rest.routes 层，依赖 infrastructure.llm
"""

from __future__ import annotations

import json

from quart import Blueprint, current_app, request, Response, jsonify

from flypig.domain.exceptions import ModelAPIError
from flypig.infrastructure.llm.openai_adapter import OpenAIAdapter

chat_bp = Blueprint("chat", __name__, url_prefix="/api")


@chat_bp.route("/chat", methods=["POST"])
async def chat():
    data = await request.get_json(force=True) or {}
    messages = data.get("messages", [])
    model_name = data.get("model", "")

    if not messages:
        return jsonify({"error": "messages 不能为空"}), 400
    if not model_name:
        return jsonify({"error": "model 不能为空"}), 400

    try:
        settings = current_app.config["flypig_settings"]
        adapter = OpenAIAdapter(model_name, settings)
    except ModelAPIError as e:
        return jsonify({"error": str(e)}), 400

    async def generate():
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

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
