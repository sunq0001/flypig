"""LangGraph 节点函数

为什么做：StateGraph 的节点需要纯函数定义，每个节点处理 AgentState 的一段逻辑。
实现方法：chat_node(model, on_token) 工厂函数，从 state.messages 调 model.stream()，
         每个 token 通过 on_token 回调实时推送给 SSE，同时收集完整响应更新状态。
         所有关键节点应用 safe_node 装饰器防止崩溃导致整图中断。

ReAct 循环中的错误处理：
  chat/execute 两个节点都被 safe_node 包裹。
  节点抛出异常 → safe_node 捕获 → 错误消息写回 messages → 走边回到 chat (或结束)。
  router 有 MAX_TURNS=25 上限，防止死循环。

技术栈：langgraph, asyncio, loguru
层&依赖：domain.agent 层，依赖 domain.interfaces.imodel + domain.agent_state
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable

from loguru import logger as _log

from flypig.domain.agent_state import AgentState
from flypig.domain.interfaces.imodel import IModel


def safe_node(node_func: Callable, node_name: str = "unknown") -> Callable:
    """装饰器：节点异常时不崩图，返回错误消息

    文档：docs/docs_refactor/langgraph-graph.md → §节点异常保护

    Args:
        node_func: 异步节点函数
        node_name: 节点名称（用于日志和 trace 标识）
    """

    @functools.wraps(node_func)
    async def wrapper(state: AgentState) -> AgentState:
        turn = state.get("turn_id", 0)
        _log.debug("[{}] 进入 (turn={})", node_name, turn)

        t0 = time.monotonic()
        try:
            result = await node_func(state)
            elapsed = time.monotonic() - t0
            _log.debug("[{}] 完成 (耗时={:.2f}s, turn={})", node_name, elapsed, result.get("turn_id", turn))
            return result
        except Exception as e:
            elapsed = time.monotonic() - t0
            _log.warning(
                "[{}] 节点异常 (耗时={:.2f}s): {}",
                node_name,
                elapsed,
                str(e)[:200],
            )
            err_msg = str(e)[:200]
            new_msgs = list(state.get("messages", []))
            new_msgs.append(
                {
                    "role": "assistant",
                    "content": f"处理出错: {err_msg}",
                }
            )
            return {
                **state,
                "messages": new_msgs,
                "turn_id": turn + 1,
            }

    return wrapper


def _extract_text_for_llm(msg: dict) -> str:
    """从消息中提取纯文本，兼容 AI SDK parts 和 OpenAI content 格式。

    前端 @ai-sdk/vue useChat 发送 parts 格式，LLM 需要 content 格式。
    """
    if msg.get("content"):
        return msg["content"]
    parts = msg.get("parts", [])
    return "".join(p.get("text", "") for p in parts if p.get("type") == "text")


def _normalize_for_llm(messages: list[dict]) -> list[dict]:
    """将消息统一为 LLM 标准 content 格式"""
    return [{"role": m.get("role", "user"), "content": _extract_text_for_llm(m)} for m in messages]


def chat_node(
    model: IModel,
    on_token: Callable[[str], None] | None = None,
) -> Callable:
    """创建对话节点

    Args:
        model: 模型适配器实例
        on_token: 可选回调，每收到一个 token 时触发（用于 SSE 实时推流）

    Returns:
        safe_node 包裹的异步节点函数
    """

    async def _chat(state: AgentState) -> AgentState:
        messages = state["messages"]
        llm_messages = _normalize_for_llm(messages)
        full_response = ""
        token_count = 0

        _log.debug("[chat] 调用 LLM, 消息数={}", len(llm_messages))
        t0 = time.monotonic()

        async for token in model.stream(llm_messages):  # pyright: ignore[reportGeneralTypeIssues]
            if token:
                full_response += token
                token_count += 1
                if on_token:
                    on_token(token)

        elapsed = time.monotonic() - t0
        _log.debug(
            "[chat] LLM 返回完成, {} tokens (耗时={:.2f}s, {:.1f} tok/s)",
            token_count,
            elapsed,
            token_count / elapsed if elapsed > 0 else 0,
        )

        new_messages = list(messages)
        new_messages.append({"role": "assistant", "content": full_response})

        return {
            **state,
            "messages": new_messages,
            "turn_id": state.get("turn_id", 0) + 1,
        }

    return safe_node(_chat, node_name="chat")
