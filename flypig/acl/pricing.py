"""pricing

为什么做：Portkey 定价 API 返回的 JSON 格式（cents/token）与领域模型 PricingEntry（USD/1M tokens）不同，ACL 负责翻译，不让外部格式污染 domain

实现方法：portkey_to_pricing_entry 函数读取 Portkey JSON 的 pricing_config.pay_as_you_go，将 cents/token 转为 USD/1M tokens，返回 PricingEntry(ValueObject)

层&依赖：acl 层，依赖 domain.pricing_entry
"""

from typing import Any

from flypig.domain.pricing_entry import PricingEntry

PRICE_KEY = "price"
PRICE_PRECISION = 4  # 价格计算保留 4 位小数
CENTS_TO_USD_FACTOR = 10000  # cents/token → USD/1M tokens 转换系数


def _cents_per_token_to_usd_per_1m(cents: float | None) -> float | None:
    """Portkey 的 cents/token → USD/1M tokens"""
    if cents is None:
        return None
    return round(cents * CENTS_TO_USD_FACTOR, PRICE_PRECISION)


def _match_model_config(
    portkey_data: dict[str, Any],
    api_model_name: str,
) -> dict[str, Any] | None:
    """在 Portkey 数据中精确或模糊匹配模型配置"""
    model_config = portkey_data.get(api_model_name)
    if not model_config:
        for key in portkey_data:
            if key == api_model_name or key.endswith("/" + api_model_name) or api_model_name in key:
                model_config = portkey_data[key]
                break
    return model_config


def _extract_price_cents(payg: dict[str, Any], token_type: str) -> float | None:
    """从 pay_as_you_go 字典中提取指定 token 类型的价格（cents）"""
    return payg.get(token_type, {}).get(PRICE_KEY)


def portkey_to_pricing_entry(
    portkey_data: dict[str, Any],
    api_model_name: str,
) -> PricingEntry | None:
    """从 Portkey 厂商定价格式提取单个模型的定价，返回领域值对象

    Portkey JSON 结构：
    {
        "deepseek-chat": {
            "pricing_config": {
                "pay_as_you_go": {
                    "request_token":           {"price": 0.027},
                    "response_token":          {"price": 0.11},
                    "cache_read_input_token":  {"price": 0.001},
                }
            }
        }
    }

    Args:
        portkey_data: Portkey 返回的完整 JSON dict
        api_model_name: Portkey 中的模型 key（如 "deepseek-chat"）

    Returns:
        PricingEntry 值对象，如果找不到对应数据则返回 None
    """
    model_config = _match_model_config(portkey_data, api_model_name)
    if not model_config:
        return None

    payg = model_config.get("pricing_config", {}).get("pay_as_you_go", {})
    input_cents = _extract_price_cents(payg, "request_token")
    output_cents = _extract_price_cents(payg, "response_token")
    cache_read_cents = _extract_price_cents(payg, "cache_read_input_token")

    input_price = _cents_per_token_to_usd_per_1m(input_cents)
    output_price = _cents_per_token_to_usd_per_1m(output_cents)
    input_cache_hit = _cents_per_token_to_usd_per_1m(cache_read_cents)

    # 必须至少包含 input 和 output 才算有效
    if input_price is not None and output_price is not None:
        return PricingEntry(
            input_price=input_price,
            output_price=output_price,
            input_cache_hit=input_cache_hit,
        )
    return None


def default_pricing_to_entry(raw: dict[str, Any]) -> PricingEntry:
    """从 model_registry.json 的 default_pricing 格式转为 PricingEntry

    default_pricing 格式：
        {"input": 0.14, "output": 0.28, "input_cache_hit": 0.0028}

    该格式已经是 USD/1M tokens，不需要单位转换。
    """
    return PricingEntry(
        input_price=raw.get("input"),
        output_price=raw.get("output"),
        input_cache_hit=raw.get("input_cache_hit"),
    )
