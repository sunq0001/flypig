"""角色值对象

为什么做：AI 可以扮演不同角色（编码助手/架构师/测试工程师），需要 Persona 值对象定义角色元数据。
实现方法：Persona(ValueObject) @dataclass(frozen=True) 包含 name, description, system_prompt。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class Persona(ValueObject):
    """角色值对象 — 不可变，按属性相等"""

    pass
