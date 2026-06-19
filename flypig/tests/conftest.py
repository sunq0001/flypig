"""pytest 共享配置

为什么做：所有测试需要共享的 fixture（DI 容器 override、测试 SQLite 数据库、Mock 模型等）。
实现方法：pytest fixture 提供 DI override（mock 所有接口）、test SQLite（内存模式）、MockLLM 等。
实现效果：测试之间隔离，不需要手动清理状态。
技术栈：pytest fixture, DI override, test SQLite

层&依赖：tests 层，依赖 pytest + core/container
细节见文档：docs/docs_refactor/architecture-guide.md → §测试策略
"""
