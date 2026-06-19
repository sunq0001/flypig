"""StateGraph 编译工厂

为什么做：LangGraph 的节点和边需要在启动时组装并编译，不能写在路由或 main 里。编译后的图缓存复用。
实现方法：GraphFactory 导入 domain/agent 的 nodes + router，组装 StateGraph → compile。~80 行。
实现效果：图构建集中在一处，新加节点只需在工厂中注册边。编译后的图可复用。
技术栈：LangGraph StateGraph, 导入 nodes+router → 编译, ~80 行

层&依赖：orchestration 层，依赖 domain/agent（nodes/router/state）
细节见文档：docs/docs_refactor/backend-modules.md → §GraphFactory、langgraph-graph.md → §一张图
"""