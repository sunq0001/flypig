"""测试 PricingEntry 值对象 — domain 层零依赖，最好测"""

from flypig.domain import PricingEntry


class TestPricingEntry:
    """定价值对象测试"""

    def test_equals_by_value(self):
        a = PricingEntry(input_price=1.0, output_price=2.0)
        b = PricingEntry(input_price=1.0, output_price=2.0)
        assert a == b

    def test_not_equals_by_different_value(self):
        a = PricingEntry(input_price=1.0, output_price=2.0)
        b = PricingEntry(input_price=2.0, output_price=2.0)
        assert a != b

    def test_defaults_to_none(self):
        entry = PricingEntry()
        assert entry.input_price is None
        assert entry.output_price is None
        assert entry.input_cache_hit is None

    def test_frozen(self):
        import pytest
        entry = PricingEntry(input_price=1.0, output_price=2.0)
        with pytest.raises(AttributeError):
            entry.input_price = 999.0
