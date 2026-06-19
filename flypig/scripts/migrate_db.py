"""数据库 Schema 迁移脚本

为什么做：版本更新后数据库表结构可能变化，需要运行迁移脚本升级 Schema。
实现方法：SQLAlchemy Alembic 或原生 SQL 执行 Schema 变更。
实现效果：更新 FlyPig 版本后不需要手动重建数据库。
技术栈：SQLAlchemy Alembic / 原生 SQL

层&依赖：scripts 层，依赖 SQLAlchemy + Alembic
细节见文档：docs/docs_refactor/resilience.md → §Schema 迁移
"""
