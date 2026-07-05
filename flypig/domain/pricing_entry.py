"""定价值对象

为什么做：每个模型有 input/output/cache_hit 单价，统一为 PricingEntry 值对象避免散落各处。
实现方法：PricingEntry(ValueObject) @dataclass(frozen=True)。

层&依赖：domain 层，依赖 shared
"""

from dataclasses import dataclass

from flypig.shared.base import ValueObject


@dataclass(frozen=True)
class PricingEntry(ValueObject):
    """模型定价值对象 — 不可变，按属性值相等

    Args:
        input_price: 输入价格（USD / 1M tokens）
        output_price: 输出价格（USD / 1M tokens）
        input_cache_hit: 缓存命中输入价格（USD / 1M tokens）
    """

    input_price: float | None = None
    output_price: float | None = None
    input_cache_hit: float | None = None
