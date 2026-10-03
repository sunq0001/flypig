"""工具调用值对象

为什么做：LLM 返回工具调用时需要记录调用信息（ID/名称/参数/结果）。
实现方法：ToolCall(ValueObject) + ToolDef(ValueObject) + ToolResult(ValueObject)。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class ToolDef(ValueObject):
    """工具定义值对象 — 描述工具的名称、参数 schema、描述"""

    def __init__(self, name: str, description: str = "", parameters: dict | None = None) -> None:
        self._name = name
        self._description = description
        self._parameters = parameters or {}

    @property
    def name(self) -> str:
        return self._name

    def to_openai_tool(self) -> dict:
        """TODO: 转换为 OpenAI 工具格式"""
        ...

    def to_anthropic_tool(self) -> dict:
        """TODO: 转换为 Anthropic 工具格式"""
        ...


class ToolCall(ValueObject):
    """工具调用值对象 — 记录 LLM 请求调用工具的完整信息"""

    def __init__(self, tool_name: str, arguments: dict, call_id: str = "") -> None:
        self._tool_name = tool_name
        self._arguments = arguments
        self._call_id = call_id
        self._result: ToolResult | None = None

    @property
    def result(self) -> "ToolResult | None":
        return self._result

    def is_pending(self) -> bool:
        """TODO: 判断调用是否等待执行"""
        return self._result is None

    def complete(self, result: "ToolResult") -> None:
        """TODO: 标记工具调用完成并记录结果"""
        ...


class ToolResult(ValueObject):
    """工具执行结果值对象 — 记录工具执行的输出和状态"""

    SUCCESS = "success"
    ERROR = "error"

    def __init__(self, output: str, status: str = SUCCESS) -> None:
        self._output = output
        self._status = status

    @property
    def output(self) -> str:
        return self._output

    def is_success(self) -> bool:
        return self._status == self.SUCCESS

    def to_sse_event(self) -> dict:
        """TODO: 转换为 SSE 事件格式"""
        return {"type": "tool-result", "output": self._output}
