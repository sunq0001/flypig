"""
test_pricing

为何做：测试 acl/pricing.py 中定价转换的所有函数（单位转换/模型匹配/价格提取/default 格式）

如何测：直接调用各函数，验证输入→输出映射正确
- _cents_per_token_to_usd_per_1m：单位转换系数和 None 处理
- _match_model_config：精确/模糊/不匹配 三种场景
- _extract_price_cents：字段提取和缺失场景
- portkey_to_pricing_entry：完整转换链路（已有 test_portkey_acl.py 覆盖）
- default_pricing_to_entry：default_pricing 格式转换

层&依赖：tests.unit 层，依赖 acl.pricing
"""

from typing import Any

from flypig.acl.pricing import (
    _cents_per_token_to_usd_per_1m,
    _extract_price_cents,
    _match_model_config,
    default_pricing_to_entry,
)
from flypig.domain import PricingEntry


class TestCentsToUsd:
    """_cents_per_token_to_usd_per_1m 单元测试"""

    def test_none_returns_none(self) -> None:
        assert _cents_per_token_to_usd_per_1m(None) is None

    def test_zero_returns_zero(self) -> None:
        assert _cents_per_token_to_usd_per_1m(0.0) == 0.0

    def test_normal_conversion(self) -> None:
        # 0.027 cents/token → 270 USD/1M tokens
        assert _cents_per_token_to_usd_per_1m(0.027) == 270.0

    def test_large_value(self) -> None:
        assert _cents_per_token_to_usd_per_1m(100.0) == 1_000_000.0

    def test_precision_rounding(self) -> None:
        # 四舍五入保留 4 位
        result = _cents_per_token_to_usd_per_1m(0.00012345)
        assert result == 1.2345


class TestMatchModelConfig:
    """_match_model_config 单元测试"""

    def test_exact_match(self) -> None:
        data = {"gpt-4": {"key": "val"}}
        assert _match_model_config(data, "gpt-4") == {"key": "val"}

    def test_fuzzy_match_prefix(self) -> None:
        data = {"azure/gpt-4": {"key": "val"}}
        assert _match_model_config(data, "gpt-4") == {"key": "val"}

    def test_fuzzy_match_substring(self) -> None:
        data = {"deepseek-chat-123": {"key": "val"}}
        assert _match_model_config(data, "deepseek-chat") == {"key": "val"}

    def test_no_match_returns_none(self) -> None:
        assert _match_model_config({"gpt-3": {}}, "gpt-4") is None

    def test_empty_data_returns_none(self) -> None:
        assert _match_model_config({}, "gpt-4") is None


class TestExtractPriceCents:
    """_extract_price_cents 单元测试"""

    def test_normal_extract(self) -> None:
        payg: dict[str, Any] = {"request_token": {"price": 0.027}}
        assert _extract_price_cents(payg, "request_token") == 0.027

    def test_missing_token_type_returns_none(self) -> None:
        payg: dict[str, Any] = {"request_token": {"price": 0.027}}
        assert _extract_price_cents(payg, "nonexistent") is None

    def test_missing_price_key_returns_none(self) -> None:
        payg: dict[str, Any] = {"request_token": {"other_key": 1.0}}
        assert _extract_price_cents(payg, "request_token") is None

    def test_empty_payg_returns_none(self) -> None:
        assert _extract_price_cents({}, "request_token") is None


class TestDefaultPricingToEntry:
    """default_pricing_to_entry 单元测试"""

    def test_all_fields(self) -> None:
        entry = default_pricing_to_entry({"input": 0.14, "output": 0.28, "input_cache_hit": 0.0028})
        assert entry.input_price == 0.14
        assert entry.output_price == 0.28
        assert entry.input_cache_hit == 0.0028

    def test_input_only(self) -> None:
        entry = default_pricing_to_entry({"input": 0.14})
        assert entry.input_price == 0.14
        assert entry.output_price is None
        assert entry.input_cache_hit is None

    def test_empty_dict(self) -> None:
        entry = default_pricing_to_entry({})
        assert entry.input_price is None
        assert entry.output_price is None
        assert entry.input_cache_hit is None

    def test_returns_pricing_entry_instance(self) -> None:
        entry = default_pricing_to_entry({"input": 1.0, "output": 2.0})
        assert isinstance(entry, PricingEntry)
