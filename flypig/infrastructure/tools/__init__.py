"""工具执行包

为什么做：AI 调用的所有工具（文件/bash/git/搜索/MCP）需要统一的执行入口和注册机制。
实现方法：ToolExecutor 调度器 + 按功能分组的工具文件（file/review/search/interact/system/mcp）+ 公共 utils。
实现效果：加新工具只需新建工具文件并在注册表中声明，不改调度器。
技术栈：LangGraph ToolNode, subprocess, aiofiles, Docker SDK

层&依赖：infrastructure.tools 层，实现 IToolExecutor，依赖 domain/interfaces
细节见文档：docs/docs_refactor/tools.md → §核心哲学
"""