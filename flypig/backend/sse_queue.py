"""SSE 队列抽象

为什么做：LangGraph 的事件需要异步推送到前端 SSE 连接，需要一个线程安全的队列抽象。
实现方法：asyncio.Queue 封装，支持多类型事件分发（token/reasoning/choice/approval/change_review/suggestion/response_end）。
实现效果：事件推送不阻塞 LangGraph 执行，前端实时接收流式事件。
技术栈：asyncio.Queue, event 类型分发

层&依赖：backend 层，依赖 asyncio
细节见文档：docs/docs_refactor/data-flow.md → §SSE 事件流
"""
