"""成本追踪"""
from typing import Optional

# DeepSeek 缓存折扣：缓存命中 token 按输入价格的 10% 计费
CACHE_DISCOUNT_RATIO = 0.1


def _format_cost(cost: float) -> str:
    """动态格式化金额：自动选择合适的小数位数"""
    if cost >= 0.01:
        return f"${cost:.4f}"
    elif cost >= 0.0001:
        return f"${cost:.6f}"
    elif cost > 0:
        return f"${cost:.2e}"
    else:
        return "$0.00"


class CostTracker:
    def __init__(self, pricing: dict):
        self.pricing = pricing
        self.reset()

    def set_pricing(self, model: str, prices: dict):
        """为指定模型设置价格"""
        self.pricing[model] = prices

    def reset(self):
        """重置会话统计"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cache_hit_tokens = 0
        self.total_cache_miss_tokens = 0
        self.total_cost = 0.0
        self.api_calls = 0

    def record(self, model: str, input_tokens: int, output_tokens: int,
               cache_hit_tokens: int = 0):
        """记录一次 API 调用，区分缓存成本"""
        self.api_calls += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cache_hit_tokens += cache_hit_tokens
        cache_miss = max(0, input_tokens - cache_hit_tokens)
        self.total_cache_miss_tokens += cache_miss

        model_pricing = self.pricing.get(model, {"input": 0, "output": 0})
        input_price = model_pricing.get("input", 0) / 1_000_000
        output_price = model_pricing.get("output", 0) / 1_000_000

        # 缓存命中按折扣价计费，未命中按全价计费
        cache_hit_cost = cache_hit_tokens * input_price * CACHE_DISCOUNT_RATIO
        cache_miss_cost = cache_miss * input_price
        output_cost = output_tokens * output_price

        call_cost = cache_hit_cost + cache_miss_cost + output_cost
        self.total_cost += call_cost

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_hit_tokens": cache_hit_tokens,
            "cost": call_cost,
        }

    def get_summary(self) -> str:
        """获取会话汇总（含缓存统计）"""
        total_tokens = self.total_input_tokens + self.total_output_tokens
        if self.total_cache_hit_tokens:
            hit_pct = 100 * self.total_cache_hit_tokens / max(1, self.total_input_tokens)
            cache_line = (f"  Cache Hit: {self.total_cache_hit_tokens:,} "
                          f"({hit_pct:.0f}% of input)\n")
        else:
            cache_line = ""
        return (
            f"Session Summary:\n"
            f"  API Calls: {self.api_calls}\n"
            f"  Total Tokens: {total_tokens:,} "
            f"(In: {self.total_input_tokens:,} / Out: {self.total_output_tokens:,})\n"
            f"{cache_line}"
            f"  Total Cost: {_format_cost(self.total_cost)}"
        )

    def format_usage(self, input_tokens: int, output_tokens: int, cost: float,
                     cache_hit_tokens: int = 0) -> str:
        """格式化单次使用信息"""
        total = input_tokens + output_tokens
        cache_info = ""
        if cache_hit_tokens:
            pct = 100 * cache_hit_tokens / max(1, input_tokens)
            cache_info = f" [Cache: {pct:.0f}% hit]"
        return f"[Tokens: {total:,}]{cache_info} [Cost: {_format_cost(cost)}]"
