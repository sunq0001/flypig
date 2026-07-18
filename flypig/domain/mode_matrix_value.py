"""
模式矩阵值对象 — 用户意图×模式的权限矩阵

TODO: 填充业务方法后移除 __init__ 中字段定义

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class ModeMatrix(ValueObject):
    """模式矩阵值对象 — 用户意图×模式的权限矩阵"""

    def __init__(self, value: str = "") -> None:
        self._value = value

    def has_permission(self) -> None:
        """TODO: ModeMatrix.has_permission"""
        pass

    def allowed_modes(self) -> None:
        """TODO: ModeMatrix.allowed_modes"""
        pass

    def to_dict(self) -> None:
        """TODO: ModeMatrix.to_dict"""
        pass
