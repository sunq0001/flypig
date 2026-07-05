"""模式权限矩阵值对象

为什么做：不同模式下用户可用的操作集不同，需要权限矩阵统一描述。
实现方法：ModeMatrix(ValueObject) @dataclass(frozen=True)，定义用户操作→模式的权限映射。

层&依赖：domain 层，依赖 shared
细节见文档：docs/docs_refactor/mode-matrix.md
"""

from flypig.shared.base import ValueObject


class ModeMatrix(ValueObject):
    """模式×权限矩阵值对象"""

    pass
