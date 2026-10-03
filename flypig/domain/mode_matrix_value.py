"""
模式矩阵值对象 — 用户意图×模式的权限矩阵

为什么做：同一个意图在不同执行模式下的权限不同，这份矩阵是「AI 建议、用户决定」
        原则的领域表达，必须集中定义而不是散落在路由里。
实现方法：ModeMatrix 持有矩阵标识，has_permission()/allowed_modes() 查询权限，
        to_dict() 供前端展示矩阵。
层&依赖：domain 层（值对象），依赖 shared
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
