"""AgentState TypedDict

为什么做：LangGraph 的每条消息都需要携带会话 ID、轮次 ID、模式、上下文约束等元数据，不能只用裸消息列表。
实现方法：TypedDict 定义 messages/turn_id/session_id/mode/context/confirmation 等字段，零依赖纯数据容器。
实现效果：状态结构自文档化，IDE 自动补全，类型安全。所有节点函数共享同一个状态定义。
技术栈：typing.TypedDict, messages/turn_id/mode/context/confirmation

层&依赖：domain.agent 层，零依赖（纯 typing）
细节见文档：docs/docs_refactor/langgraph-graph.md → §AgentState
"""