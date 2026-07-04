"""LangGraph 节点函数

为什么做：同一张 StateGraph 内的所有处理步骤需要拆分为独立节点。

实现方法：Python 函数作为 LangGraph 节点，接收 AgentState → 调用 LLM → 返回更新后的 AgentState。
R1 阶段只有 chat_node（最小可对话），后续轮次逐步添加 ask_choice/execute/lint/review/suggest 等节点。

实现效果：每个节点专注一个职责，测试可独立 mock。

技术栈：LangGraph nodes, chat_node 初版

层&依赖：domain.agent 层，依赖 state.py + domain/interfaces/imodel.py
细节见文档：docs/docs_refactor/langgraph-graph.md → §全路径一览
"""

from __future__ import annotations

from flypig.orchestration.state import AgentState
from flypig.domain.exceptions import ModelAPIError
from flypig.domain.interfaces.imodel import IModel
from flypig.shared.constants import ERROR_TRUNCATE_LENGTH as TRUNCATE_LENGTH


def chat_node(model: IModel) -> callable:
    """创建 chat_node（依赖注入方式，避免全局变量）

    Args:
        model: IModel 适配器实例

    Returns:
        LangGraph 节点函数
    """

    async def _chat_node(state: AgentState) -> dict:
        try:
            messages = state["messages"]
            response_content = ""

            async for token in model.stream(messages):
                response_content += token

            new_messages = list(messages)
            new_messages.append({"role": "assistant", "content": response_content})

            return {
                "messages": new_messages,
                "turn_id": state.get("turn_id", 0) + 1,
            }
        except ModelAPIError:
            return {
                "messages": messages + [{"role": "assistant", "content": "模型服务暂不可用，请稍后重试"}],
                "error": "model_api_error",
            }
        except Exception as e:
            return {
                "messages": messages + [{"role": "assistant", "content": f"处理出错: {str(e)[:TRUNCATE_LENGTH]}"}],
                "error": str(e),
            }

    return _chat_node
