"""
MCP 服务器值对象 — MCP 协议的服务端配置

为什么做：外部 MCP 服务器的连接信息与工具清单属于领域概念，
        需要统一建模，避免各处裸字典传递。
实现方法：McpServer 持有服务器标识，暴露 is_connected()/list_tools()/call_tool()
        表达领域语义，具体协议实现交给 infrastructure 的 ACL。
层&依赖：domain 层（值对象），依赖 shared
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
