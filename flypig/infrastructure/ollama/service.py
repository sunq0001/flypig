"""service

为什么做：封装 Ollama HTTP API，提供本地模型的生命周期管理

实现方法：OllamaLocalModelService 通过 acl.ollama 适配器调用 Ollama API（/api/tags、/api/pull），
         实现 ILocalModelService 接口

层&依赖：infrastructure.ollama 层，实现 domain.interfaces.ilocal_model_service
"""

from __future__ import annotations

import asyncio
import subprocess
import time

from loguru import logger

from flypig.acl.ollama import fetch_tag_names, probe
from flypig.domain.interfaces.ilocal_model_service import ILocalModelService
from flypig.domain.registry import ModelRegistry
from flypig.shared.settings import AppSettings

OLLAMA_CHECK_TIMEOUT = 2
DEFAULT_LIST_CACHE_TTL = 30
LIST_TIMEOUT = 2
CACHE_KEY_MODELS = "models"
CACHE_KEY_TS = "ts"

# Ollama 官方 tags 接口路径
_TAGS_PATH = "/api/tags"
# Windows 主机上的 Ollama 兜底地址
_DEFAULT_WINDOWS_HOST = "host.docker.internal"


def _is_wsl() -> bool:
    """检测是否运行在 WSL 环境"""
    try:
        with open("/proc/version", encoding="ascii", errors="ignore") as f:
            return "microsoft" in f.read().lower() or "wsl" in f.read().lower()
    except Exception:
        return False


def _wsl_windows_host() -> str:
    """获取 WSL 中访问 Windows 主机的 IP（默认网关）"""
    host = ""
    try:
        host = subprocess.check_output(
            ["sh", "-c", "ip route show | grep default | awk '{print $3}'"],
            timeout=3,
            text=True,
        ).strip()
    except Exception:
        host = ""
    if host:
        return host
    logger.debug("[ollama] 未探测到 WSL 网关，回退默认主机 {}", _DEFAULT_WINDOWS_HOST)
    return _DEFAULT_WINDOWS_HOST


_WSL_DETECTED = _is_wsl()
_WINDOWS_OLLAMA_URL = f"http://{_wsl_windows_host()}:11434"


class OllamaLocalModelService(ILocalModelService):
    """Ollama 本地模型服务 — 实现 ILocalModelService"""

    def __init__(
        self,
        settings: AppSettings,
        registry: ModelRegistry,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._cache: dict = {CACHE_KEY_MODELS: [], CACHE_KEY_TS: 0.0}

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

    def _probe_urls(self) -> list[str]:
        """返回要探测的 Ollama URL 列表（优先官方配置，WSL 下追加 Windows Ollama）"""
        primary = self._base_url
        urls = [primary]
        if _WSL_DETECTED:
            # WSL 下若 primary 是 localhost，追加 Windows 主机上的 Ollama
            parsed = primary.replace("http://", "").replace("https://", "")
            if parsed.startswith("localhost") or parsed.startswith("127.0.0.1"):
                urls.append(_WINDOWS_OLLAMA_URL)
        return urls

    async def _try_urls(self, path: str, timeout: int) -> str | None:
        """按顺序探测多个 URL，返回第一个响应的 base_url"""
        for url in self._probe_urls():
            try:
                if await probe(url, path, timeout):
                    return url
            except Exception as e:
                logger.debug("[ollama] 探测 {} 失败: {}", url, e)
                continue
        return None

    def _to_local_model(self, name: str, base_url: str, api_path: str, provider: str) -> dict:
        """组装本地模型条目（前端 /api/config/local-models 消费的格式）"""
        return {
            "name": name,
            "provider": provider,
            "base_url": f"{base_url}{api_path}",
            "api_model": name,
            "local": True,
            "has_key": True,
        }

    # ── interface implementation ──

    async def check_running(self) -> bool:
        timeout = self._local_cfg.get("check_timeout", OLLAMA_CHECK_TIMEOUT)
        return await self._try_urls(_TAGS_PATH, timeout) is not None

    async def list_models(self) -> list[dict]:
        now = time.time()
        cache_ttl = self._local_cfg.get("list_cache_ttl", DEFAULT_LIST_CACHE_TTL)
        timeout = self._local_cfg.get("list_timeout", LIST_TIMEOUT)
        api_path = self._local_cfg.get("api_path", "/v1")
        provider = self._local_cfg.get("provider", "Local")

        if now - self._cache[CACHE_KEY_TS] < cache_ttl:
            return self._cache[CACHE_KEY_MODELS]

        found_url = await self._try_urls(_TAGS_PATH, timeout)
        if not found_url:
            return []

        # 把探测到的 URL 写回 settings，供 OpenAIAdapter 等后续模块使用
        if self._settings.ollama_base_url != found_url:
            self._settings.ollama_base_url = found_url

        names = await fetch_tag_names(found_url, timeout)
        result = [self._to_local_model(n, found_url, api_path, provider) for n in names]
        self._cache[CACHE_KEY_MODELS] = result
        self._cache[CACHE_KEY_TS] = now
        return result

    async def list_installed_names(self) -> list[str]:
        return [m["name"] for m in await self.list_models()]

    async def pull_model(self, model_name: str) -> None:
        binary = self._local_cfg.get("binary", "ollama")
        proc = await asyncio.create_subprocess_exec(
            binary,
            "pull",
            model_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await proc.wait()
