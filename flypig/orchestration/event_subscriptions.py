"""事件订阅编排

为什么做：不同服务（用量追踪/checkpoint/日志）需要订阅特定事件，需要统一的声明式订阅管理。
实现方法：EventSubscriptions 声明哪个模块订阅哪些事件（tool:after/turn:start/turn:end），按事件类型分发。~60 行。
实现效果：加新订阅只需在此文件中加一行声明，不需要改钩子系统。
技术栈：hook register/emit, 声明谁订阅哪些事件, ~60 行

层&依赖：orchestration 层，依赖 domain/interfaces/ihook.py
细节见文档：docs/docs_refactor/backend-modules.md → §EventSubscriptions
"""