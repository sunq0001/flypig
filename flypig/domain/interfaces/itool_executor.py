"""工具执行器接口

为什么做：所有工具（文件操作/bash/git/搜索/MCP）的调用需要统一入口，不能散落在各个节点中调用。
实现方法：IToolExecutor ABC 定义 execute() 核心方法，接收 tool_call → 路由到具体实现 → 返回原始结果。支持 MCP 工具动态注册。
实现效果：新加工具只需加一个工具文件并在注册表中声明，ToolExecutor 和 LangGraph 代码都不用改。
技术栈：IToolExecutor ABC, MCP 动态注册, tool_call → 原始结果

层&依赖：domain.interfaces 层，零依赖
细节见文档：docs/docs_refactor/tools.md → §核心哲学、subprocess.md → §执行策略
"""