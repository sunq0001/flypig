"""对话编排主服务

为什么做：用户消息进来到 SSE 事件分发出去需要一个编排服务，不能直接在路由里写 LangGraph 调用。
实现方法：ChatService 接收用户输入 → 调用 LangGraph StateGraph → 将逐 token 事件分发到 SSE 队列。~60 行。
实现效果：路由层只处理 HTTP 协议，编排逻辑集中在 ChatService 中，测试可 mock。
技术栈：LangGraph, SSE 事件分发, receive → invoke → dispatch, ~60 行

层&依赖：orchestration 层（编排服务），依赖 domain/agent（nodes/router/state）+ GraphFactory
细节见文档：docs/docs_refactor/data-flow.md → §后端数据流、backend-modules.md → §ChatService
"""
