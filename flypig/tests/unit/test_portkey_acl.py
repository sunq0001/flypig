"""test_portkey_acl

为什么做：测试 ACL 层的 Portkey 格式转换是否正确

实现方法：构造 Portkey JSON 数据，调用 portkey_to_pricing_entry，验证返回的 PricingEntry 属性值

层&依赖：tests.unit 层，依赖 acl.pricing
"""

from flypig.acl.pricing import portkey_to_pricing_entry


class TestPortkeyACL:
    """Portkey 定价格式转换测试"""

    def test_normal_conversion(self):
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
        assert result.input_price == 270.0
        assert result.output_price == 1100.0
        assert result.input_cache_hit == 10.0

    def test_fuzzy_match(self):
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
        result = portkey_to_pricing_entry({}, "nonexistent-model")
        assert result is None

    def test_missing_pricing_returns_none(self):
        raw = {"some-model": {"pricing_config": {}}}
        result = portkey_to_pricing_entry(raw, "some-model")
        assert result is None
