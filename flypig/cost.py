"""成本追踪"""
from typing import Optional


class CostTracker:
    def __init__(self, pricing: dict):
        self.pricing = pricing
        self.reset()
    
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
            f"  Total Cost: ${self.total_cost:.4f}"
        )
    
    def format_usage(self, input_tokens: int, output_tokens: int, cost: float) -> str:
        """格式化单次使用信息"""
        total = input_tokens + output_tokens
        return f"[Tokens: {total:,}] [Cost: ${cost:.4f}]"


def format_token_count(tokens: int) -> str:
    """格式化 token 数量"""
    if tokens < 1000:
        return str(tokens)
    elif tokens < 1000000:
        return f"{tokens/1000:.1f}K"
    else:
        return f"{tokens/1000000:.1f}M"
