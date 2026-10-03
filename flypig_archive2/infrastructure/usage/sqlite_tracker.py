"""SQLite 用量追踪实现

为什么做：每轮对话的 token/cost/cache 用量需要持久化存储，SQLite 对单用户场景足够且零依赖部署。
实现方法：SQLAlchemy 读写 turn_usage/call_usage 表，~80 行。共享 conversations.db 的 WAL 模式连接。
实现效果：用量数据自动入表，用户可在前端查询历史和统计。
技术栈：SQLAlchemy, turn_usage/call_usage 表, ~80 行

层&依赖：infrastructure.usage 层，实现 IUsageTracker，依赖 SQLAlchemy
细节见文档：docs/docs_refactor/mem_convStore_usage.md → §数据模型
"""
