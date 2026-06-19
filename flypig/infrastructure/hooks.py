"""事件钩子系统

为什么做：工具调用/对话轮次等事件需要挂载副作用（日志/用量/checkpoint），钩子系统提供统一的 register/emit 机制。
实现方法：register(event_type, hook) → emit(event_type, context) 按 priority 顺序调度。TurnCheckpointHook 默认启用。
实现效果：加新副作用只需实现 IHook 并注册，不影响原有事件流程。
技术栈：register/emit, priority 排序, TurnCheckpointHook 默认启用

层&依赖：infrastructure 层，实现 domain/interfaces/ihook.py 定义的钩子系统
细节见文档：docs/docs_refactor/resilience.md → §TurnCheckpointHook
"""