"""MCP 服务器值对象

为什么做：MCP 工具服务器配置（名称/命令/参数/env）需要统一数据结构。
实现方法：McpServer(ValueObject) @dataclass(frozen=True)。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class McpServer(ValueObject):
    """MCP 服务器配置值对象"""

    pass
