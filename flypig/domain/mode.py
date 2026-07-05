"""模式枚举 + 配置值对象

为什么做：Explore/Plan/Execute 三种模式需要枚举定义和对应的配置信息（温度/工具集/身份）。
实现方法：ExecutionMode(Enum) + ModeConfig(ValueObject)。
技术栈：ExecutionMode enum, ModeConfig ValueObject

层&依赖：domain 层，零依赖
细节见文档：docs/docs_refactor/mode-matrix.md → §核心矩阵
"""

from enum import Enum, auto

from flypig.shared.base import ValueObject


class ExecutionMode(Enum):
    EXPLORE = auto()
    PLAN = auto()
    EXECUTE = auto()


class ModeConfig(ValueObject):
    """模式配置值对象 — 温度范围/可用工具列表/默认 prompt 身份"""

    pass
