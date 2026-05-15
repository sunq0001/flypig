"""成本追踪"""
from typing import Optional


def _format_cost(cost: float) -> str:
    """动态格式化金额：自动选择合适的小数位数"""
    if cost >= 0.01:
        return f"${cost:.4f}"
    elif cost >= 0.0001:
        return f"${cost:.6f}"
    elif cost > 0:
        # 非常小的金额，用科学记数法
        return f"${cost:.2e}"
    else:
        return "$0.00"


class CostTracker:
    def __init__(self, pricing: dict):
        self.pricing = pricing
        self.reset()
    
    def set_pricing(self, model: str, prices: dict):
        """为指定模型设置价格（用于注入动态获取的价格）"""
        self.pricing[model] = prices

    def reset(self):
        """重置会话统计"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.api_calls = 0
    
    def record(self, model: str, input_tokens: int, output_tokens: int):
        """记录一次 API 调用"""
        self.api_calls += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        # 计算费用
        model_pricing = self.pricing.get(model, {"input": 0, "output": 0})
        input_cost = input_tokens * model_pricing.get("input", 0) / 1_000_000
        output_cost = output_tokens * model_pricing.get("output", 0) / 1_000_000
        self.total_cost += input_cost + output_cost
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": input_cost + output_cost
        }
    
    def get_summary(self) -> str:
        """获取会话汇总"""
        total_tokens = self.total_input_tokens + self.total_output_tokens
        return (
            f"Session Summary:\n"
            f"  API Calls: {self.api_calls}\n"
            f"  Total Tokens: {total_tokens:,} "
            f"(In: {self.total_input_tokens:,} / Out: {self.total_output_tokens:,})\n"
            f"  Total Cost: {_format_cost(self.total_cost)}"
        )
    
    def format_usage(self, input_tokens: int, output_tokens: int, cost: float) -> str:
        """格式化单次使用信息"""
        total = input_tokens + output_tokens
        return f"[Tokens: {total:,}] [Cost: {_format_cost(cost)}]"


def format_token_count(tokens: int) -> str:
    """格式化 token 数量"""
    if tokens < 1000:
        return str(tokens)
    elif tokens < 1000000:
        return f"{tokens/1000:.1f}K"
    else:
        return f"{tokens/1000000:.1f}M"
