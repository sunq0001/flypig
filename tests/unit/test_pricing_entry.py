"""test_pricing_entry

为什么做：测试 PricingEntry 值对象的不可变性、相等性、默认值

实现方法：直接构造 PricingEntry 实例，验证 __eq__、__ne__、frozen 等特性

层&依赖：tests.unit 层，依赖 domain.pricing_entry
"""

import pytest

from flypig.domain import PricingEntry


class TestPricingEntry:
    """定价值对象测试"""

    def test_equals_by_value(self) -> None:
        a = PricingEntry(input_price=1.0, output_price=2.0)
        b = PricingEntry(input_price=1.0, output_price=2.0)
        assert a == b

    def test_not_equals_by_different_value(self) -> None:
        a = PricingEntry(input_price=1.0, output_price=2.0)
        b = PricingEntry(input_price=2.0, output_price=2.0)
        assert a != b

    def test_defaults_to_none(self) -> None:
        entry = PricingEntry()
        assert entry.input_price is None
        assert entry.output_price is None
        assert entry.input_cache_hit is None

    def test_frozen(self) -> None:
        entry = PricingEntry(input_price=1.0, output_price=2.0)
        with pytest.raises(AttributeError):
            entry.input_price = 999.0
