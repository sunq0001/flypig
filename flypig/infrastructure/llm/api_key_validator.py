"""LLMApiKeyValidator — HTTP 调用验证 API Key

为什么做：用户通过 UI 输入 API Key 后，需要先调一次厂商 API 确认 Key 有效再保存。
         接口层不应直接发 HTTP 请求，此职责属于基础设施层。

实现方法：从 ModelRegistry 获取厂商的 base_url 和 api_model，发一个 max_tokens=1 的测试请求。
         200 OK → 有效；401 → 无效；402/403/429/含"余额不足"→ Key 有效但余额不足。

层&依赖：infrastructure.llm 层，实现 domain.interfaces.iapikey_validator + 依赖 domain.registry
"""

from __future__ import annotations

import httpx
from loguru import logger

from flypig.domain.interfaces.iapikey_validator import IApiKeyValidator, KeyValidationResult
from flypig.domain.registry import ModelRegistry


class LLMApiKeyValidator(IApiKeyValidator):
    """通过发测试请求验证 API Key 有效性"""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    async def validate(self, provider: str, api_key: str) -> KeyValidationResult:
        base_url = ""
        api_model = ""
        for meta in self._registry.all_models.values():
            if meta.get("provider") == provider:
                base_url = meta.get("base_url", "")
                api_model = meta.get("api_model", "")
                break

        if not base_url or not api_model:
            return KeyValidationResult(False, f"未找到 {provider} 的 API 地址")

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": api_model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 1,
                    },
                )

                if r.status_code == 200:  # noqa: PLR2004
                    return KeyValidationResult(True, "API Key 有效")
                if r.status_code == 401:  # noqa: PLR2004
                    return KeyValidationResult(False, "API Key 无效，请检查后重试")

                body = r.text[:200]
                if r.status_code in (402, 403, 429) or any(
                    kw in body for kw in ("余额", "balance", "credit", "insufficient")
                ):
                    return KeyValidationResult(True, "API Key 有效（余额不足）")

                return KeyValidationResult(False, f"API 返回异常 ({r.status_code}): {body}")

        except httpx.ConnectError:
            return KeyValidationResult(False, f"无法连接到 {base_url}，请检查网络")
        except Exception as e:
            logger.warning("[apikey] 验证异常: {}", str(e)[:100])
            return KeyValidationResult(False, f"验证失败: {str(e)[:100]}")
