"""StateGraph 编译工厂

为什么做：LangGraph 的节点和边需要在启动时组装并编译，不能写在路由或 main 里。编译后的图缓存复用。

实现方法：GraphFactory 导入 domain/agent 的 nodes，组装 StateGraph → compile。
R1 阶段只有 1 个 chat_node + 1 条入口边，R2 起逐步添加 ToolNode 等。

实现效果：图构建集中在一处，新加节点只需在工厂中注册边。

技术栈：LangGraph StateGraph, 导入 nodes → 编译

层&依赖：orchestration 层，依赖 domain/agent（nodes/state）+ domain/interfaces（IModel）
细节见文档：docs/docs_refactor/backend-modules.md → §GraphFactory、langgraph-graph.md → §一张图
"""

from __future__ import annotations

from langgraph.graph import StateGraph, START

from domain.agent.nodes import chat_node
from domain.agent.state import AgentState
from domain.interfaces.imodel import IModel


class GraphFactory:
    """LangGraph 编译工厂"""

    def __init__(self, model: IModel):
        self._model = model
        self._graphs: dict[str, callable] = {}

    def _build_graph(self) -> callable:
        """构建并编译 StateGraph"""
        builder = StateGraph(AgentState)

        # R1: 只有 chat_node
        builder.add_node("chat", chat_node(self._model))

        # 入口边：START → chat
        builder.add_edge(START, "chat")

        return builder.compile()

    def get_graph(self, session_id: str) -> callable:
        """获取会话对应的编译图（按 session_id 隔离）"""
        if session_id not in self._graphs:
            self._graphs[session_id] = self._build_graph()
        return self._graphs[session_id]

    def clear_graph(self, session_id: str) -> None:
        """清理会话图"""
        self._graphs.pop(session_id, None)
