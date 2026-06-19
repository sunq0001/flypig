"""Agent 接口

为什么做：AI Agent 的核心交互逻辑需要统一接口定义，便于测试和替换。
实现方法：IAgent ABC 定义 run/stop/status 核心方法，LangGraphAgent 实现基于 StateGraph 的对话流程。
实现效果：换 Agent 实现（如从 LangGraph 切换到自定义状态机）不需要改调用方代码。
技术栈：IAgent ABC

层&依赖：domain.interfaces 层，依赖 AgentState（domain/agent/state.py）
细节见文档：docs/docs_refactor/langgraph-graph.md → §一张图
"""