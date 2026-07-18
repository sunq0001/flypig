"""
MCP 服务器值对象 — MCP 协议的服务端配置

TODO: 填充业务方法后移除 __init__ 中字段定义

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class McpServer(ValueObject):
    """MCP 服务器值对象 — MCP 协议的服务端配置"""

    def __init__(self, value: str = "") -> None:
        self._value = value

    def is_connected(self) -> None:
        """TODO: McpServer.is_connected"""
        pass

    def list_tools(self) -> None:
        """TODO: McpServer.list_tools"""
        pass

    def call_tool(self) -> None:
        """TODO: McpServer.call_tool"""
        pass
