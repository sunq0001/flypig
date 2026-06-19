"""应用生命周期事件

为什么做：启动时需要初始化资源（数据库连接、MCP 服务器），关闭时需要清理（关闭线程池、保存状态），需要一个标准事件机制串联。
实现方法：提供 before_server_start / after_server_stop 等 hook 调用点，模块注册自己的启动/关闭回调。
实现效果：模块可以独立注册生命周期逻辑，不用侵入 __main__.py。启动/关闭流程清晰可控。
技术栈：asyncio, Signal/Event bus

层&依赖：core 层，依赖 logging
细节见文档：docs/docs_refactor/resilience.md → §启动恢复流程
"""
