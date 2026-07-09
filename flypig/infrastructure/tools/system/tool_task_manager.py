"""任务看板 CRUD 工具

为什么做：AI 需要创建/更新/反馈任务，不能通过裸 SQL 操作数据库。
实现方法：封装 IConversationStore 的任务 CRUD（add_task/update_task/update_feedback），任务数据写入 conversations.db。
实现效果：AI 在对话中创建的任务自动同步到任务看板，前端实时更新。
技术栈：add_task/update_task/update_feedback, 写入 conversations.db

层&依赖：infrastructure.tools.system 层，依赖 IConversationStore
细节见文档：docs/docs_refactor/mem_convStore_tasks.md → §CRUD
"""

# TODO: 骨架文件占位，待具体实现
