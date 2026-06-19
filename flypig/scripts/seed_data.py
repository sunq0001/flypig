"""测试数据填充脚本

为什么做：开发/演示环境需要模拟的对话/任务/用量数据用于测试和展示。
实现方法：SQLAlchemy 写入模拟的会话/轮次/任务/用量记录到 conversations.db。
实现效果：dev 环境有可视化数据，不需要从零开始聊。
技术栈：SQLAlchemy, 模拟对话/任务/用量

层&依赖：scripts 层，依赖 SQLAlchemy
细节见文档：docs/docs_refactor/operations.md → §测试数据
"""
