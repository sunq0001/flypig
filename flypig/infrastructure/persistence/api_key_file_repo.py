"""ApiKeyFileRepository — JSON 文件实现 IApiKeyRepository

为什么做：通过 UI 保存的 API Key 需要持久化到文件，进程重启后可用。
         不写回 config.yaml（用户手工管理的配置文件），存到 data/api_keys.json。

实现方法：读写 JSON 文件，每行一个 provider→key 映射。
         提供一个公共函数 load_api_keys_from_file()，供 bootstrap/settings.py 在
         DI 容器就绪前调用。

层&依赖：infrastructure.persistence 层，实现 domain.interfaces.iapikey_repository
"""

from __future__ import annotations

import json
from pathlib import Path

from flypig.domain.interfaces.iapikey_repository import IApiKeyRepository


def _get_keys_path() -> Path:
    """默认 API Key 文件路径：flypig/data/api_keys.json"""
    return Path(__file__).resolve().parent.parent.parent / "data" / "api_keys.json"


# ── bootstrap 启动时加载用（DI 容器未就绪） ──


def load_api_keys_from_file() -> dict[str, str]:
    """从 data/api_keys.json 读取已保存的 API Key

    供 bootstrap/settings.py 在启动时调用（此时 DI 容器尚未就绪）。
    """
    path = _get_keys_path()
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return dict(json.load(f))
    except Exception:
        return {}


# ── 完整仓储实现 ──


class ApiKeyFileRepository(IApiKeyRepository):
    """基于 JSON 文件的 API Key 仓储"""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _get_keys_path()

    def load_all(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            with open(self._path, encoding="utf-8") as f:
                return dict(json.load(f))
        except Exception:
            return {}

    def save(self, provider: str, api_key: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        keys = self.load_all()
        keys[provider] = api_key
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(keys, f, ensure_ascii=False, indent=2)
