"""Ollama 本地模型服务实现

实现 domain.interfaces.ilocal_model_service.ILocalModelService，
封装所有 Ollama HTTP 调用。

配置数据全部来自 model_registry.json 的 local 段（超时、缓存TTL、API路径等）。
"""

from __future__ import annotations

import asyncio
import time

import httpx

from flypig.shared.settings import AppSettings
from flypig.domain.interfaces.ilocal_model_service import ILocalModelService
from flypig.domain.registry import ModelRegistry


class OllamaLocalModelService(ILocalModelService):
    """Ollama 本地模型服务 — 实现 ILocalModelService"""

    def __init__(
        self,
        settings: AppSettings,
        registry: ModelRegistry,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._cache: dict = {"models": [], "ts": 0.0}

    # ── internal helpers ──

    @property
    def _base_url(self) -> str:
        url = self._settings.ollama_base_url
        if not url:
            url = self._local_cfg.get("default_ollama_url", "")
        return url

    @property
    def _local_cfg(self) -> dict:
        return self._registry.get_local_config()

    # ── interface implementation ──

    async def check_running(self) -> bool:
        timeout = self._local_cfg.get("check_timeout", 2)
        try:
            resp = await httpx.AsyncClient().get(
                f"{self._base_url}/api/tags", timeout=timeout
            )
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[dict]:
        now = time.time()
        cache_ttl = self._local_cfg.get("list_cache_ttl", 30)
        timeout = self._local_cfg.get("list_timeout", 2)
        api_path = self._local_cfg.get("api_path", "/v1")
        provider = self._local_cfg.get("provider", "Local")

        if now - self._cache["ts"] < cache_ttl:
            return self._cache["models"]

        try:
            resp = await httpx.AsyncClient().get(
                f"{self._base_url}/api/tags", timeout=timeout
            )
            if resp.status_code != 200:
                return []

            result = []
            for m in resp.json().get("models", []):
                name = m.get("name", "")
                if not name:
                    continue
                result.append({
                    "name": name,
                    "provider": provider,
                    "base_url": f"{self._base_url}{api_path}",
                    "api_model": name,
                    "local": True,
                    "has_key": True,
                })

            self._cache["models"] = result
            self._cache["ts"] = now
            return result
        except Exception:
            return []

    async def list_installed_names(self) -> list[str]:
        return [m["name"] for m in await self.list_models()]

    async def pull_model(self, model_name: str) -> None:
        binary = self._local_cfg.get("binary", "ollama")
        proc = await asyncio.create_subprocess_exec(
            binary, "pull", model_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await proc.wait()
