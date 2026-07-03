"""Ollama ACL — 防腐层，封装所有 Ollama HTTP 调用

配置数据全部来自 model_registry.json 的 local 段（超时、缓存TTL、API路径等）。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import httpx

from flypig.bootstrap.settings import AppSettings
from flypig.domain.model_ref import get_local_config


@dataclass
class OllamaACL:
    settings: AppSettings
    _cache: dict = field(default_factory=lambda: {"models": [], "ts": 0.0})

    @property
    def _base_url(self) -> str:
        url = self.settings.ollama_base_url
        if not url:
            url = self._local_cfg.get("default_ollama_url", "")
        return url

    @property
    def _local_cfg(self) -> dict:
        return get_local_config()

    def check_running(self) -> bool:
        timeout = self._local_cfg.get("check_timeout", 2)
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[dict]:
        now = time.time()
        cache_ttl = self._local_cfg.get("list_cache_ttl", 30)
        timeout = self._local_cfg.get("list_timeout", 2)
        api_path = self._local_cfg.get("api_path", "/v1")
        provider = self._local_cfg.get("provider", "Local")

        if now - self._cache["ts"] < cache_ttl:
            return self._cache["models"]

        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=timeout)
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

    def list_installed_names(self) -> list[str]:
        return [m["name"] for m in self.list_models()]

    async def pull_model(self, model_name: str) -> None:
        binary = self._local_cfg.get("binary", "ollama")
        proc = await asyncio.create_subprocess_exec(
            binary, "pull", model_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await proc.wait()
