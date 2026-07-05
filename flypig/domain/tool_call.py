"""工具调用/定义/结果值对象

为什么做：工具调用需要统一数据结构（tool_call / tool_def / tool_result），不能散落成 dict。
实现方法：三个 ValueObject，均由 @dataclass(frozen=True) 定义。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class ToolCall(ValueObject):
    """工具调用值对象 — 记录单次工具调用的参数和上下文"""

    pass


class ToolDef(ValueObject):
    """工具定义值对象 — 描述工具的名称、参数 schema、描述"""

    pass


class ToolResult(ValueObject):
    """工具执行结果值对象 — 记录工具执行的输出和状态"""

    pass
