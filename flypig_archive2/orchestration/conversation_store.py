"""统一 SQLite 存储

为什么做：对话/任务/checkpoint/用量/建议/定价/代码图谱需要统一的持久化存储，7 张表共享同一个 SQLite WAL 数据库。
实现方法：IConversationStore 的 SQLAlchemy 实现，conversations.db 含 7 张表，WAL 模式并发读写。
实现效果：所有持久化需求由一个 store 覆盖，事务一致性强。数据库文件只有几百 KB。
技术栈：SQLAlchemy ORM, conversations.db 7 表, WAL 模式

层&依赖：orchestration 层，实现 domain/interfaces/iconversation_store.py
细节见文档：docs/docs_refactor/mem_convStore.md → §所有表、mem_convStore_tasks.md → §任务状态
"""
