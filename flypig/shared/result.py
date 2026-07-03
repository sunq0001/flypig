"""Result 类型 — 显式处理成功/失败，代替异常

Ok(value) / Err(error) 模式，避免 try/except 传播。调用 unwrap() 获取值，
失败时抛 UnwrapError（继承 FlyPigException）。

层&依赖：shared 层，零依赖
"""

from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass
class Result(Generic[T, E]):
    """Result 类型 — 显式处理成功/失败，代替异常

    使用方式：
        def transfer(...) -> Result[bool, str]:
            if insufficient:
                return Result.err("余额不足")
            return Result.ok(True)

        result = transfer(...)
        if result.is_ok:
            print(result.unwrap())
        else:
            print(result.error)
    """
    _value: Optional[T] = None
    _error: Optional[E] = None

    @property
    def is_ok(self) -> bool:
        return self._error is None

    @property
    def is_err(self) -> bool:
        return self._error is not None

    @property
    def error(self) -> Optional[E]:
        return self._error

    def unwrap(self) -> T:
        """安全取出成功值，失败时抛异常"""
        if self._error is not None:
            raise ValueError(f"Called unwrap on error: {self._error}")
        return self._value  # type: ignore

    @classmethod
    def ok(cls, value: T) -> "Result[T, E]":
        return cls(_value=value)

    @classmethod
    def err(cls, error: E) -> "Result[T, E]":
        return cls(_error=error)
