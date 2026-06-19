"""历史会话路由 (/api/sessions)

为什么做：用户需要查看历史会话列表、创建新会话、恢复断点。
实现方法：Quart 端点，通过 SessionService 查询/创建/恢复会话。restore 返回消息列表 + AgentState。
实现效果：用户可在历史列表中找到之前的对话，点击断点恢复继续对话。
技术栈：Quart, SessionService, CRUD + restore

层&依赖：backend.routes 层，依赖 orchestration/session_service.py
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点
"""