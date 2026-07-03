"""测试 ACL 层 — Portkey JSON → PricingEntry 转换"""

from flypig.acl.pricing import portkey_to_pricing_entry
from flypig.domain import PricingEntry


class TestPortkeyACL:
    """Portkey 定价格式转换测试"""

    def test_normal_conversion(self):
        """标准 Portkey JSON 正确转为 PricingEntry"""
        raw = {
            "deepseek-chat": {
                "pricing_config": {
                    "pay_as_you_go": {
                        "request_token": {"price": 0.027},
                        "response_token": {"price": 0.11},
                        "cache_read_input_token": {"price": 0.001},
                    }
                }
            }
        }
        result = portkey_to_pricing_entry(raw, "deepseek-chat")
        assert result is not None
        assert result.input_price == 270.0     # 0.027 * 10000
        assert result.output_price == 1100.0    # 0.11 * 10000
        assert result.input_cache_hit == 10.0   # 0.001 * 10000

    def test_fuzzy_match(self):
        """模型名带路径前缀时模糊匹配"""
        raw = {
            "azure/deepseek-chat": {
                "pricing_config": {
                    "pay_as_you_go": {
                        "request_token": {"price": 0.03},
                        "response_token": {"price": 0.12},
                    }
                }
            }
        }
        result = portkey_to_pricing_entry(raw, "deepseek-chat")
        assert result is not None
        assert result.input_price == 300.0

    def test_missing_model_returns_none(self):
        """找不到模型数据返回 None"""
        result = portkey_to_pricing_entry({}, "nonexistent-model")
        assert result is None

    def test_missing_pricing_returns_none(self):
        """JSON 结构不全返回 None"""
        raw = {"some-model": {"pricing_config": {}}}
        result = portkey_to_pricing_entry(raw, "some-model")
        assert result is None
