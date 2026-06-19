"""SSE 聊天路由 (/api/chat)

为什么做：前端 useChat 通过 POST /api/chat 发送用户消息，后端返回 SSE 流式事件。
实现方法：Quart SSE 端点，接收用户消息 → ChatService.invoke() → LangGraph → 逐 token 写入 SSE 响应流。≤120 行。
实现效果：前端一行 useChat 接管 SSE 消费，后端专注编排。
技术栈：Quart SSE, ChatService → LangGraph, ≤120 行

层&依赖：backend.routes 层，依赖 orchestration/chat_service.py + sse_queue.py
细节见文档：docs/docs_refactor/api-reference.md → §SSE 事件格式、data-flow.md → §后端数据流
"""