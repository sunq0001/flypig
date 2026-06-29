"""SSE 聊天路由 (/api/chat)

为什么做：前端 useChat 通过 POST /api/chat 发送用户消息，后端返回 AI SDK v4 UI Message Chunk SSE 流。

实现方法：
- POST /api/chat 接收 {messages, model}
- 创建 OpenAIAdapter → stream 输出 AI SDK v4 text-delta 格式
- useChat(DefaultChatTransport) 原生消费

实现效果：前端 useChat 接管 SSE 消费，打字机效果、错误处理、tool_call 原生支持。

技术栈：Quart SSE, AI SDK v4 UI Message Chunk 格式

层&依赖：backend.routes 层，依赖 infrastructure.llm.openai_adapter
细节见文档：docs/docs_refactor/api-reference.md → §SSE 事件格式
"""

from __future__ import annotations

import json

from quart import Blueprint, current_app, request, Response, jsonify

from domain.config.config import Config
from domain.exceptions import ModelAPIError
from domain.config.model_registry import REGISTRY
from infrastructure.llm.openai_adapter import OpenAIAdapter

chat_bp = Blueprint("chat", __name__, url_prefix="/api")


@chat_bp.route("/chat", methods=["POST"])
async def chat():
    """SSE 对话端点 — OpenAI 兼容格式"""
    data = await request.get_json(force=True) or {}
    messages = data.get("messages", [])
    model_name = data.get("model", "")

    if not messages:
        return jsonify({"error": "messages 不能为空"}), 400
    if not model_name:
        return jsonify({"error": "model 不能为空"}), 400
    if model_name not in REGISTRY:
        return jsonify({"error": f"未知模型: {model_name}"}), 400

    try:
        config = current_app.config.get("flypig_config") or Config()
        adapter = OpenAIAdapter(model_name, config)
    except ModelAPIError as e:
        return jsonify({"error": str(e)}), 400

    async def generate():
        try:
            # AI SDK v4 UI Message Chunk 格式
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
