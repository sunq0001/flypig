"""历史搜索路由 (/api/history/search)

为什么做：用户需要搜索历史对话内容，而不是逐条翻看。
实现方法：Quart GET 端点，通过 SQLite FTS5 搜索对话历史记录。
实现效果：用户输入关键词即可找到相关的历史轮次和消息。
技术栈：Quart, FTS5/search, GET

层&依赖：backend.routes 层，依赖 orchestration/conversation_store.py
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点
"""