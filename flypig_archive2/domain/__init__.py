"""FlyPig 领域层

为什么做：AI 对话的核心概念（消息、会话、模式、工具、评分、任务）需要统一的数据定义和行为约束。
实现方法：domain 层定义所有接口（interfaces/）、数据类（models/）、LangGraph 节点和状态（agent/）、prompt 管理（prompts/）、配置数据类（config/）、统一异常（exceptions.py）。
实现效果：下层模块依赖接口而非具体实现，替换实现不影响核心逻辑。
技术栈：ABC, @dataclass, TypedDict, Enum, LangGraph

层&依赖：domain 层（最内层），不依赖任何其他 flypig 模块
细节见文档：docs/docs_refactor/architecture-guide.md → §核心原则
"""
