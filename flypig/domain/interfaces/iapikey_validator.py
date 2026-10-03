"""API Key 验证接口

为什么做：不同厂商的 API Key 验证逻辑可能不同（HTTP调用/OAuth/本地模型不需要验证），
         统一接口屏蔽差异，domain service 无需关注实现细节。

实现方法：ABC 定义 validate 方法，infrastructure 层实现具体验证逻辑。

层&依赖：domain.interfaces 层，依赖 domain 异常体系
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class KeyValidationResult:
    """API Key 验证结果值对象

    - valid: True=Key有效（含余额不足），False=Key无效
    - message: 给用户显示的消息
    """
    valid: bool = False
    message: str = ""


class IApiKeyValidator(ABC):
    """API Key 验证器 — 调用厂商 API 确认 Key 是否有效"""

    @abstractmethod
    async def validate(self, provider: str, api_key: str) -> KeyValidationResult:
        """验证 API Key 是否有效

        Args:
            provider: 厂商显示名（如 "DeepSeek"）
            api_key: 待验证的 API Key

        Returns:
            KeyValidationResult
        """
        ...
