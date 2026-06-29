"""会话状态管理服务

为什么做：用户与 AI 的对话以会话为单位组织，需要支持多会话创建/切换/销毁/持久化/断点恢复。
实现方法：SessionService 封装 IConversationStore 的会话 CRUD，提供 restore() 方法读取断点数据和消息历史。~100 行。
实现效果：用户可创建多个对话会话，关闭后回来可继续之前的对话。
技术栈：多会话 CRUD + restore() 断点恢复, ~100 行

层&依赖：orchestration 层，依赖 domain/interfaces/iconversation_store.py
细节见文档：docs/docs_refactor/backend-modules.md → §SessionService、resilience.md → §崩溃恢复
"""
