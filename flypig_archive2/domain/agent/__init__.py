"""LangGraph 节点与状态包

为什么做：AI 对话的流程控制（分析→问用户→执行→审查→建议）需要状态机管理，不能手写 if-else 控制流。
实现方法：基于 LangGraph StateGraph，统一的状态 + 节点函数 + 条件路由。模式只影响 context 约束，不影响图拓扑。
实现效果：对话流程由 LLM 自行决定路径，不需要硬编码流水线。加新行为只需加节点 + 注册边。
技术栈：LangGraph, StateGraph, TypedDict

层&依赖：domain.agent 层，依赖 domain/interfaces（IModel 等）+ domain/models（Message 等）
细节见文档：docs/docs_refactor/langgraph-graph.md → §一张图
"""
