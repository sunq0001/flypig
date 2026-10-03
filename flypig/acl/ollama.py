"""Ollama 适配器（ACL）

为什么做：Ollama 的 HTTP 协议（/api/tags 返回结构、状态码语义）属于外部系统细节，
         不能让 infrastructure 层直接依赖，否则 API 变更会污染领域/基础设施代码。
实现方法：用 httpx 封装「探测可用性」与「拉取模型名列表」两个纯函数，
         输入外部 URL → 输出领域可直接消费的纯数据（模型名列表）。
层&依赖：acl 层，仅依赖 httpx 与标准库
"""

from __future__ import annotations

from http import HTTPStatus

import httpx

# Ollama 模型列表接口
_TAGS_PATH = "/api/tags"


async def probe(url: str, path: str, timeout: int) -> bool:
    """探测某个 base_url 上的 Ollama 接口是否可用（HTTP 200 视为可用）"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{url}{path}", timeout=timeout)
    except Exception:
        return False
    return resp.status_code == HTTPStatus.OK


async def fetch_tag_names(base_url: str, timeout: int) -> list[str]:
    """拉取 /api/tags，返回已安装模型名列表（外部 JSON → 纯数据）"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base_url}{_TAGS_PATH}", timeout=timeout)
    except Exception:
        return []

    if resp.status_code != HTTPStatus.OK:
        return []
    return [m.get("name", "") for m in resp.json().get("models", []) if m.get("name")]
