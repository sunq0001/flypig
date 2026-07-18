"""API Key 领域服务 — 验证通过后才保存 API Key

为什么做：API Key 的「验证通过后才保存」是领域逻辑，不应放在 interface 层。
         由 IApiKeyValidator 负责验证，IApiKeyRepository 负责持久化，
         本服务编排两者的顺序和决策。

实现方法：DomainService 模式，构造器注入两个依赖，暴露 validate_and_save 方法。

层&依赖：domain.services 层，依赖 domain.interfaces 的 IApiKeyValidator + IApiKeyRepository
"""

from __future__ import annotations

from loguru import logger

from flypig.domain.interfaces.iapikey_repository import IApiKeyRepository
from flypig.domain.interfaces.iapikey_validator import IApiKeyValidator, KeyValidationResult
from flypig.shared.kernel.domain_service import DomainService


class ApiKeyService(DomainService):
    """API Key 领域服务 — 先验证、验证通过再保存"""

    def __init__(
        self,
        validator: IApiKeyValidator,
        repository: IApiKeyRepository,
    ) -> None:
        self._validator = validator
        self._repository = repository

    async def validate_and_save(self, provider: str, api_key: str) -> KeyValidationResult:
        """验证 API Key，有效则持久化

        Args:
            provider: 厂商显示名
            api_key: API Key

        Returns:
            验证结果（valid=True 时同时完成持久化）
        """
        result = await self._validator.validate(provider, api_key)

        if result.valid:
            logger.info("[apikey] {} Key 验证通过: {}", provider, result.message)
            self._repository.save(provider, api_key)
        else:
            logger.warning("[apikey] {} Key 验证失败: {}", provider, result.message)

        return result
