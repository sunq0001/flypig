"""ToolExecutor 调度器

为什么做：LLM 返回 tool_call 后需要一个调度器按工具名路由到具体的实现函数，不能手写 if-else。
实现方法：ToolExecutor 接收 tool_call → 查找注册表中对应的实现 → 执行 → 返回原始结果。支持 MCP 工具动态注册。
实现效果：加新工具只需注册到 ToolNode，调度器代码不变。
技术栈：LangGraph ToolNode, tool_call → 执行 → 原始结果

层&依赖：infrastructure.tools 层，实现 IToolExecutor，依赖所有工具函数
细节见文档：docs/docs_refactor/tools.md → §核心哲学、subprocess.md → §执行策略
"""
