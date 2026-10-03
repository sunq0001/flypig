"""路由逻辑单元测试

为什么做：LangGraph 路由函数需要独立测试，确保各条件边跳转正确。
实现方法：mock AgentState，测试每个条件边函数返回的下一节点名是否正确。
实现效果：路由逻辑变更后有测试兜底。
技术栈：pytest, mock AgentState

层&依赖：tests.unit 层，依赖 domain/agent/router.py
细节见文档：docs/docs_refactor/langgraph-graph.md → §Router
"""
