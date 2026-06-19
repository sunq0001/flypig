"""任务 CRUD 路由 (/api/tasks/*)

为什么做：用户需要在前端看板中查看和管理任务列表，以及回溯某 turn 时的任务快照。
实现方法：Quart 端点实现 CRUD + search + stats + at-turn 快照 + 历史，通过 IConversationStore 查询。
实现效果：前端任务看板实时同步 AI 创建的任务，回溯时任务状态回到之前的状态。
技术栈：Quart, CRUD + search + stats + history/snapshot

层&依赖：backend.routes 层，依赖 orchestration/conversation_store.py
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点、mem_convStore_tasks.md → §CRUD
"""