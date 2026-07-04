"""防腐层 — Portkey 定价格式 → 领域定价值对象

为什么做：Portkey 定价 API 返回的 JSON 结构（cents/token）与领域模型的
PricingEntry（USD/1M tokens）格式不同，ACL 负责翻译，不让外部格式污染 domain。

使用方法：
    from flypig.acl.pricing import portkey_to_pricing_entry

    raw = httpx.get("https://api.portkey.ai/...").json()
    entry = portkey_to_pricing_entry(raw, "deepseek-chat")

如果 Portkey 改 API 格式，只需要改这个文件，domain 层和 infrastructure 层不动。

层&依赖：acl 层，依赖 domain.pricing_entry.PricingEntry
"""

from typing import Any, Optional

from flypig.domain.pricing_entry import PricingEntry


PRICE_PRECISION = 4  # 价格计算保留 4 位小数
CENTS_TO_USD_FACTOR = 10000  # cents/token → USD/1M tokens 转换系数


def _cents_per_token_to_usd_per_1m(cents: Optional[float]) -> Optional[float]:
    """Portkey 的 cents/token → USD/1M tokens"""
    if cents is None:
        return None
    return round(cents * CENTS_TO_USD_FACTOR, PRICE_PRECISION)


def portkey_to_pricing_entry(
    portkey_data: dict[str, Any],
    api_model_name: str,
) -> Optional[PricingEntry]:
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
    # 先精确匹配，再模糊匹配
    model_config = portkey_data.get(api_model_name)
    if not model_config:
        for key in portkey_data:
            if key == api_model_name or key.endswith("/" + api_model_name) or api_model_name in key:
                model_config = portkey_data[key]
                break
        if not model_config:
            return None

    payg = model_config.get("pricing_config", {}).get("pay_as_you_go", {})
    input_cents = payg.get("request_token", {}).get("price")
    output_cents = payg.get("response_token", {}).get("price")
    cache_read_cents = payg.get("cache_read_input_token", {}).get("price")

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
