"""API Key 仓储接口

为什么做：API Key 的持久化需要统一接口，支持文件/数据库/Linux密钥环等多种实现。
实现方法：ABC 定义 save/load_all，infrastructure 层实现具体存储后端。

层&依赖：domain.interfaces 层，零外部依赖
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class IApiKeyRepository(ABC):
    """API Key 仓储 — 持久化 UI 保存的 API Key"""

    @abstractmethod
    def load_all(self) -> dict[str, str]:
        """加载所有已保存的 API Key

        Returns:
            {provider_name: api_key} 字典
        """
        ...

    @abstractmethod
    def save(self, provider: str, api_key: str) -> None:
        """保存某个厂商的 API Key

        Args:
            provider: 厂商显示名（如 "DeepSeek"、"OpenAI"）
            api_key: API Key 值
        """
        ...
