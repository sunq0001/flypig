"""ModelRegistry — 模型注册表域服务

从 model_registry.json 加载所有模型配置、厂商元数据、定价配置、本地配置。
DDD 域服务，封装所有 JSON 读取逻辑，不暴露全局变量。

层&依赖：domain 层
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from flypig.shared.base import DomainService


class ModelRegistry(DomainService):
    """模型注册表 — 封装 model_registry.json 的所有读取逻辑"""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir or Path(__file__).resolve().parent.parent / "data"
        self._path = self._data_dir / "model_registry.json"
        self._registry: dict[str, dict] = {}
        self._provider_key_map: dict[str, str] = {}
        self._load()

    # ── internal ──

    def _load(self) -> None:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        models_raw = raw.get("models", {})
        self._registry = dict(models_raw)
        self._provider_key_map = {}
        for name, meta in models_raw.items():
            provider = meta.get("provider", "")
            key_attr = meta.get("key_attr", "")
            if provider and key_attr:
                self._provider_key_map[provider] = key_attr
        self._raw = raw

    # ── public API ──

    @property
    def all_models(self) -> dict[str, dict]:
        """所有模型元数据（原始 dict，只读）"""
        return dict(self._registry)

    @property
    def provider_key_map(self) -> dict[str, str]:
        """provider → key_attr 映射"""
        return dict(self._provider_key_map)

    def resolve(self, name: str) -> Optional[dict]:
        """获取单个模型元数据"""
        return self._registry.get(name)

    def known_models(self) -> list[str]:
        """所有已注册模型名列表"""
        return list(self._registry.keys())

    def get_provider_meta(self, name: str) -> Optional[dict]:
        """获取某个模型的厂商元数据（icon/color/display_name）"""
        meta = self._registry.get(name)
        if not meta:
            return None
        return {
            "icon": meta.get("icon", ""),
            "color": meta.get("color", ""),
            "display_name": meta.get("display_name", ""),
        }

    def get_local_config(self) -> dict:
        """获取 local 配置段（本地模型元数据）"""
        return dict(self._raw.get("local", {}))

    def get_pricing_config(self) -> dict:
        """获取 pricing 配置段"""
        return dict(self._raw.get("pricing", {}))

    def get_portkey_provider(self, model_name: str) -> str:
        """获取模型的 Portkey 提供商名（有覆盖走覆盖，否则 provider.lower()）"""
        meta = self._registry.get(model_name, {})
        override = meta.get("portkey_provider")
        if override:
            return override
        return meta.get("provider", "").lower()
