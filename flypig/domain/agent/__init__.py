"""Agent 包 — LangGraph 节点 + 路由

为什么做：统一导出 domain.agent 下的节点和路由函数。
实现方法：从各子模块导入后在 __all__ 中暴露。
层&依赖：domain 层
"""

from flypig.domain.agent.exec_node import execute_node
from flypig.domain.agent.nodes import chat_node
from flypig.domain.agent.router import router

__all__ = [
    "chat_node",
    "execute_node",
    "router",
]
