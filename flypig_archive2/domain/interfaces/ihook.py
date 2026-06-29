"""事件钩子接口

为什么做：工具调用前后、对话轮次变更等事件需要挂载副作用（日志/用量记录/checkpoint），钩子系统提供统一注册/触发机制。
实现方法：IHook ABC 定义 on_event() 方法，EventBus 按 priority 顺序调度已注册的钩子。
实现效果：加新钩子不需要改原有逻辑，只需实现 IHook 并注册。checkpoint/用量/日志都是钩子实现。
技术栈：IHook ABC, priority 排序, register/emit

层&依赖：domain.interfaces 层，零依赖
细节见文档：docs/docs_refactor/resilience.md → §TurnCheckpointHook
"""
