"""条件边路由逻辑

为什么做：LangGraph 需要根据当前状态决定下一个节点（继续 chat / 出选择 / 执行工具 / 审查），不能硬编码跳转。
实现方法：条件路由函数，基于 AgentState 中的 tool_calls、confirmation、mode 等字段返回下一节点名。
实现效果：路由逻辑集中可测，加新节点不需要改现有路由逻辑。
技术栈：LangGraph conditional_edges, tool_calls 判断, 4 种条件边

层&依赖：domain.agent 层，依赖 state.py
细节见文档：docs/docs_refactor/langgraph-graph.md → §Router
"""