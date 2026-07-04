"""validation

为什么做：校验工具，收集错误不抛异常，避免 try/except 散落在业务代码中

实现方法：ValidationResult 收集错误列表，Validator 组合多条校验规则

层&依赖：shared 层
"""

from dataclasses import dataclass, field
from typing import Callable, Generic, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class ValidationResult:
    """校验结果 — 收集错误，不抛异常

    使用方式：
        result = ValidationResult()
        if not name:
            result.add_error("名称不能为空")
        if len(name) > 50:
            result.add_error("名称不能超过50个字符")
        if not result.is_valid:
            return result
    """
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.is_valid = False
        self.errors.append(msg)

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
        )


class Validator(Generic[T]):
    """校验器 — 组合多条校验规则

    使用方式：
        validator = Validator[str]()
        validator.add_rule(lambda n: len(n) > 0, "名称不能为空")
        result = validator.validate("")
    """

    def __init__(self) -> None:
        self._rules: List[tuple[Callable[[T], bool], str]] = []

    def add_rule(self, predicate: Callable[[T], bool], message: str) -> None:
        self._rules.append((predicate, message))

    def validate(self, value: T) -> ValidationResult:
        result = ValidationResult()
        for predicate, message in self._rules:
            if not predicate(value):
                result.add_error(message)
        return result
