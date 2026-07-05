"""变更评分值对象

为什么做：AI 修改代码前需要评估影响范围，按风险等级决定审批方式（自动/通知/阻塞）。
实现方法：ChangeScore(ValueObject) 包含 level, risk_reason, affected_files。
技术栈：ValueObject, enum.Enum

层&依赖：domain 层，依赖 shared
细节见文档：docs/docs_refactor/adversarial-system.md → §ChangeScore
"""

from enum import Enum, auto

from flypig.shared.base import ValueObject


class ChangeLevel(Enum):
    TRIVIAL = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class ChangeScore(ValueObject):
    """变更评分值对象 — 按风险等级决定审批策略"""

    pass
