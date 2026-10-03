"""LLMApiKeyValidator — 通过 ACL 探测验证 API Key

为什么做：用户通过 UI 输入 API Key 后，需要先调一次厂商 API 确认 Key 有效再保存。
         接口层不应直接发 HTTP 请求，基础设施层也不应直接持有外部 API 格式，
         因此 HTTP 细节全部下沉到 acl/llm_api.py。
实现方法：从 ModelRegistry 取厂商 base_url / api_model，经 ACL 发一次
         max_tokens=1 的探测请求，再按状态码判定：
         200 → 有效；401 → 无效；402/403/429 或含余额关键词 → 有效但余额不足。
层&依赖：infrastructure.llm 层，实现 domain.interfaces.iapikey_validator + 依赖 acl.llm_api
"""

from __future__ import annotations

from http import HTTPStatus

from loguru import logger

from flypig.acl.llm_api import probe_chat_completion
from flypig.domain.interfaces.iapikey_validator import IApiKeyValidator, KeyValidationResult
from flypig.domain.registry import ModelRegistry

# ── 探测参数 ──
_PROBE_TIMEOUT = 15
_ERROR_BODY_CHARS = 200

# 这些状态码表示「Key 有效但账户不可用（欠费/限流）」
_INSUFFICIENT_CODES = (
    HTTPStatus.PAYMENT_REQUIRED,
    HTTPStatus.FORBIDDEN,
    HTTPStatus.TOO_MANY_REQUESTS,
)
_INSUFFICIENT_KEYWORDS = ("余额", "balance", "credit", "insufficient")


class LLMApiKeyValidator(IApiKeyValidator):
    """通过发测试请求验证 API Key 有效性"""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def _resolve_endpoint(self, provider: str) -> tuple[str, str]:
        """从注册表取该厂商的 (base_url, api_model)，找不到返回空串"""
        for meta in self._registry.all_models.values():
            if meta.get("provider") == provider:
                return meta.get("base_url", ""), meta.get("api_model", "")
        return "", ""

    def _interpret(self, status_code: int, body: str) -> KeyValidationResult:
        """按状态码/响应体判定 Key 状态"""
        if status_code == HTTPStatus.OK:
            return KeyValidationResult(True, "API Key 有效")
        if status_code == HTTPStatus.UNAUTHORIZED:
            return KeyValidationResult(False, "API Key 无效，请检查后重试")

        body = body[:_ERROR_BODY_CHARS]
        if status_code in _INSUFFICIENT_CODES or any(kw in body for kw in _INSUFFICIENT_KEYWORDS):
            return KeyValidationResult(True, "API Key 有效（余额不足）")

        return KeyValidationResult(False, f"API 返回异常 ({status_code}): {body}")

    async def validate(self, provider: str, api_key: str) -> KeyValidationResult:
        base_url, api_model = self._resolve_endpoint(provider)
        if not base_url or not api_model:
            return KeyValidationResult(False, f"未找到 {provider} 的 API 地址")

        try:
            status_code, body = await probe_chat_completion(
                base_url, api_model, api_key, _PROBE_TIMEOUT
            )
        except Exception as e:
            logger.warning("[apikey] 验证异常: {}", str(e)[:_ERROR_BODY_CHARS])
            return KeyValidationResult(False, f"验证失败: {str(e)[:_ERROR_BODY_CHARS]}")

        return self._interpret(status_code, body)
