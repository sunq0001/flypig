"""LLM HTTP API 适配器（ACL）

为什么做：OpenAI 兼容端点的 HTTP 细节（路径拼接、请求体字段、返回结构）
         属于外部系统格式，不应散落在 infrastructure 层；
         API Key 校验这类探测请求统一走本适配器。
实现方法：用 httpx 发一次最小 chat/completions 请求，返回 (状态码, 响应体文本)，
         由调用方按业务语义判定 Key 状态。
层&依赖：acl 层，仅依赖 httpx 与标准库
"""

from __future__ import annotations

import httpx

# OpenAI 兼容的补全路径
_CHAT_COMPLETIONS_PATH = "/chat/completions"
_WWW_AUTH_JSON = "application/json"


async def probe_chat_completion(
    base_url: str,
    api_model: str,
    api_key: str,
    timeout: int,
) -> tuple[int, str]:
    """发一次 max_tokens=1 的探测请求

    Returns:
        (HTTP 状态码, 响应体文本)
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}{_CHAT_COMPLETIONS_PATH}",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": _WWW_AUTH_JSON,
            },
            json={
                "model": api_model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            },
        )
    return resp.status_code, resp.text
