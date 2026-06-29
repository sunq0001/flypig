"""对话存储接口

为什么做：对话记录、任务、用量、checkpoint、建议反馈需要统一存储和检索，存储方式（SQLite/PostgreSQL/S3）可替换。
实现方法：IConversationStore ABC 定义会话/轮次/任务/checkpoint/用量/建议的 CRUD 方法。
实现效果：切换数据库后端只需换实现类，所有业务代码不变。对话/任务/用量共享同一数据源。
技术栈：IConversationStore ABC, SQLite/S3 可替换, 7 表 CRUD

层&依赖：domain.interfaces 层，依赖 domain/models 中的 Message/Session/Task 数据类
细节见文档：docs/docs_refactor/mem_convStore.md → §所有表、mem_convStore_tasks.md → §任务状态
"""
