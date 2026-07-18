"""API Key 值对象

为什么做：外部 LLM 提供商需要 API Key 认证，Key 需加密存储。
实现方法：ApiKey(ValueObject) 封装 Key 的掩码和验证逻辑。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class ApiKey(ValueObject):
    """API Key 值对象"""

    def __init__(self, provider: str, key: str) -> None:
        self._provider = provider
        self._key = key

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def masked(self) -> str:
        """返回掩码后的 Key（只显示末 4 位）"""
        return f"{self._provider}:****{self._key[-4:]}" if len(self._key) > 4 else "****"

    def is_valid_format(self) -> bool:
        """TODO: 验证 Key 格式是否合法"""
        return len(self._key) > 0
