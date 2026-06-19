"""LangGraph 节点函数

为什么做：同一张 StateGraph 内的所有处理步骤需要拆分为独立节点（chat/ask_choice/execute/lint/review/suggest）。
实现方法：Python 函数作为 LangGraph 节点，接收 AgentState → 调用 LLM/工具 → 返回更新后的 AgentState。
实现效果：每个节点专注一个职责，测试可独立 mock。新加行为只需加函数 + 注册边。
技术栈：LangGraph nodes, chat/ask_choice/execute/lint/review/suggest

层&依赖：domain.agent 层，依赖 state.py + domain/interfaces（IModel/IToolExecutor）+ domain/models
细节见文档：docs/docs_refactor/langgraph-graph.md → §全路径一览
"""