"""Agent 接口

为什么做：AI Agent 的核心交互逻辑需要统一接口定义，便于测试和替换。

实现方法：IAgent ABC 定义 run（输入用户消息 → 异步迭代事件流）/ stop（中断当前执行）/ status（查询状态）三个核心方法。
LangGraphAgent 实现基于 StateGraph 的统一对话流程（chat_node + router + 条件边）。

实现效果：换 Agent 实现（如从 LangGraph 切换到自定义状态机）不需要改调用方代码。

技术栈：ABC, @abstractmethod, AsyncGenerator

层&依赖：domain.interfaces 层，依赖 domain/agent/state.py（AgentState）
细节见文档：docs/docs_refactor/langgraph-graph.md → §一张图
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class IAgent(ABC):
    """AI Agent 核心接口"""

    @abstractmethod
    async def run(
        self, user_input: str, session_id: str | None = None, **kwargs
    ) -> AsyncGenerator[dict, None]:
        """处理用户输入，异步生成事件流

        Args:
            user_input: 用户消息文本
            session_id: 会话 ID，None 表示新建会话
            **kwargs: 扩展参数（mode / persona 等）

        Yields:
            事件字典，chat_service 根据事件类型推 SSE 到前端：
            {"type": "token", "content": "..."}       — 文本 token
            {"type": "tool_call", "tool": "...", ...}  — 工具调用
            {"type": "error", "message": "..."}       — 错误

        Raises:
            ModelAPIError: 模型调用失败
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """中断当前执行（用户点击停止按钮时调用）"""
        ...

    @abstractmethod
    async def status(self) -> dict:
        """返回当前 Agent 状态

        Returns:
            {"running": bool, "session_id": str | None, "mode": str, ...}
        """
        ...
