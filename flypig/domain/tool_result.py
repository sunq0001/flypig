"""兼容导入 — ToolResult 定义在 tool_call.py 中

为什么做：保持从 domain.tool_result 导入的旧代码兼容性。

实现方法：re-export，从 flypig.domain.tool_call 导入 ToolResult。

层&依赖：domain 层
"""
from flypig.domain.tool_call import ToolResult  # noqa: F401
