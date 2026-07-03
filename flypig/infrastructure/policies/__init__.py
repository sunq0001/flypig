"""执行策略包

为什么做：IModelPolicy 定义策略接口，infrastructure.policies 提供具体实现，
包括重试、熔断、超时等策略的组合。

使用方式：
    from flypig.infrastructure.policies import RetryPolicy, CircuitBreaker
"""

from flypig.infrastructure.llm.circuit_breaker import CircuitBreaker
from flypig.infrastructure.llm.retry_policy import RetryPolicy

__all__ = [
    "CircuitBreaker",
    "RetryPolicy",
]
