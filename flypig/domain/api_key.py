"""API Key 值对象

为什么做：各厂商 API Key 的配置/验证/加密需要统一数据结构。
实现方法：ApiKey(ValueObject) @dataclass(frozen=True)，只封装 key 元数据，不存明文。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class ApiKey(ValueObject):
    """API Key 元数据值对象"""
    pass
