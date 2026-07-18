"""定价值对象

为什么做：每个模型有 input/output/cache_hit 单价，统一为 PricingEntry 值对象避免散落各处。
实现方法：PricingEntry(ValueObject) @dataclass(frozen=True)。

TODO: 填充业务方法后移除 __init__ 中字段定义

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

    def total_cost(self, input_tokens: int, output_tokens: int) -> float:
        """TODO: 计算总费用"""
        return 0.0

    def to_display(self) -> str:
        """TODO: 格式化为显示文本"""
        return ""

    def currency_symbol(self) -> str:
        """TODO: 返回货币符号"""
        return "$"
