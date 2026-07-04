"""specification

为什么做：规格模式将业务规则封装为可组合的对象，支持 and_ / or_ / not_ 组合

实现方法：ABC + Generic[T]，定义 is_satisfied_by 抽象方法 + and_/or_/not_ 组合方法

层&依赖：shared 层
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class Specification(ABC, Generic[T]):
    """规格模式 — 将业务规则封装为可组合的对象

    使用方式：
        class HighValueOrder(Specification[Order]):
            def is_satisfied_by(self, order: Order) -> bool:
                return order.total > 10000

        spec = HighValueOrder().and_(IsPaid())
        if spec.is_satisfied_by(my_order):
            ...
    """

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """判断候选对象是否满足规格"""
        ...

    def and_(self, other: "Specification[T]") -> "AndSpecification[T]":
        return AndSpecification(self, other)

    def or_(self, other: "Specification[T]") -> "OrSpecification[T]":
        return OrSpecification(self, other)

    def not_(self) -> "NotSpecification[T]":
        return NotSpecification(self)


class AndSpecification(Specification[T]):
    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) and self._right.is_satisfied_by(candidate)


class OrSpecification(Specification[T]):
    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) or self._right.is_satisfied_by(candidate)


class NotSpecification(Specification[T]):
    def __init__(self, spec: Specification[T]) -> None:
        self._spec = spec

    def is_satisfied_by(self, candidate: T) -> bool:
        return not self._spec.is_satisfied_by(candidate)
