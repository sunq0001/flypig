"""config_routes

为什么做：前端需要获取/修改应用配置（工作目录、API Key、本地模型等）

实现方法：REST 路由组：workspace/apikey/browse/mkdir/local-models/local-models/pull

层&依赖：interface.rest.routes 层
"""

from __future__ import annotations

import asyncio
from http import HTTPStatus
from pathlib import Path

from flypig.domain.registry import ModelRegistry
from flypig.infrastructure.ollama.service import OllamaLocalModelService
from quart import Blueprint, current_app, jsonify, request

HTTP_BAD_REQUEST = 400
COLOR_KEY = "color"
DISPLAY_NAME_KEY = "display_name"

config_bp = Blueprint("config", __name__, url_prefix="/api/config")


def _get_settings():
    return current_app.config["flypig_settings"]


def _get_registry() -> ModelRegistry:
    return current_app.config["flypig_model_registry"]


ICON_KEY = "icon"


def _build_providers() -> dict:
    """从注册表重建厂商元数据字典（前端需要 icon/color/display_name）"""
    registry = _get_registry()
    providers: dict[str, dict] = {}
    for name, meta in registry.all_models.items():
        provider = meta.get("provider", "")
        if not provider or provider in providers:
            continue
        providers[provider] = {
            ICON_KEY: meta.get(ICON_KEY, ""),
            COLOR_KEY: meta.get(COLOR_KEY, ""),
            DISPLAY_NAME_KEY: meta.get(DISPLAY_NAME_KEY, ""),
        }
    # 本地厂商来自 JSON local 段
    local = registry.get_local_config()
    providers[local.get("provider", "Local")] = {
        ICON_KEY: local.get(ICON_KEY, "mdi:laptop"),
        COLOR_KEY: local.get(COLOR_KEY, "#888"),
        DISPLAY_NAME_KEY: local.get(DISPLAY_NAME_KEY, "本地"),
    }
    return providers


@config_bp.route("", methods=["GET"])
async def get_config() -> dict:
    cfg = _get_settings()
    registry = _get_registry()

    models = []
    for name in registry.known_models():
        meta = registry.resolve(name)
        if meta is None:
            continue
        provider = meta["provider"]
        attr = registry.provider_key_map.get(provider, "")
        has_key = bool(getattr(cfg, attr, None))
        models.append(
            {
                "name": name,
                "provider": provider,
                "base_url": meta.get("base_url", ""),
                "api_model": meta.get("api_model", ""),
                "local": False,
                "has_key": has_key,
            }
        )
    # 本地模型通过 OllamaLocalModelService 动态获取
    local_service = OllamaLocalModelService(cfg, registry)
    models.extend(await local_service.list_models())

    return jsonify(
        {
            "default_model": cfg.default_model,
            "workspace": cfg.workspace,
            "log_level": cfg.log_level,
            "models": models,
            "providers": _build_providers(),
        }
    )


@config_bp.route("", methods=["PUT"])
async def update_config() -> dict:
    data = await request.get_json(force=True) or {}
    cfg = _get_settings()
    if "default_model" in data:
        cfg.default_model = data["default_model"]
    return jsonify({"ok": True})


@config_bp.route("/workspace", methods=["POST"])
async def set_workspace() -> dict:  # type: ignore[misc]
    data = await request.get_json(force=True)
    path = (data or {}).get("path", "")
    if not path:
        return jsonify({"error": "path required"}), HTTPStatus.BAD_REQUEST

    p = Path(path).resolve()
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)

    cfg = _get_settings()
    cfg.workspace = str(p)
    return jsonify({"workspace": str(p)})


@config_bp.route("/apikey", methods=["POST"])
async def save_apikey() -> dict:  # type: ignore[misc]
    data = await request.get_json(force=True)
    provider = (data or {}).get("provider", "")
    api_key = (data or {}).get("api_key", "")
    if not provider or not api_key:
        return jsonify({"error": "provider and api_key required"}), HTTPStatus.BAD_REQUEST

    cfg = _get_settings()
    registry = _get_registry()
    attr = registry.provider_key_map.get(provider, "")
    if hasattr(cfg, attr):
        setattr(cfg, attr, api_key)
    return jsonify({"ok": True})


@config_bp.route("/browse", methods=["POST"])
async def browse():
    data = await request.get_json(force=True)
    path = (data or {}).get("path", ".")
    p = Path(path).resolve()

    if not p.exists() or not p.is_dir():
        return jsonify({"error": "目录不存在", "path": str(p)}), HTTPStatus.NOT_FOUND

    entries = []
    try:
        for entry in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                entries.append(
                    {
                        "name": entry.name,
                        "type": "directory" if entry.is_dir() else "file",
                    }
                )
            except PermissionError:
                continue
    except PermissionError:
        return jsonify({"error": "无权限访问", "path": str(p)}), HTTPStatus.FORBIDDEN

    return jsonify(
        {"path": str(p), "parent": str(p.parent) if p.parent != p else None, "entries": entries}
    )


@config_bp.route("/mkdir", methods=["POST"])
async def mkdir():
    data = await request.get_json(force=True)
    parent = (data or {}).get("parent", "")
    name = (data or {}).get("name", "")
    if not parent or not name:
        return jsonify({"error": "parent and name required"}), HTTPStatus.BAD_REQUEST
    p = Path(parent).resolve() / name
    try:
        p.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        return jsonify({"error": "无权限创建目录"}), HTTPStatus.FORBIDDEN
    return jsonify({"path": str(p), "name": name})


# ── 本地模型引导 ──


@config_bp.route("/local-models", methods=["GET"])
async def get_local_models():
    cfg = _get_settings()
    registry = _get_registry()
    service = OllamaLocalModelService(cfg, registry)

    ollama_running = await service.check_running()
    installed = await service.list_installed_names() if ollama_running else []

    return jsonify(
        {
            "running": ollama_running,
            "installed": installed,
            "ollama_base_url": cfg.ollama_base_url,
        }
    )


@config_bp.route("/local-models/pull", methods=["POST"])
async def pull_local_model() -> dict:  # type: ignore[misc]
    data = await request.get_json(force=True) or {}
    model = data.get("model", "")
    if not model:
        return jsonify({"error": "model required"}), HTTP_BAD_REQUEST

    cfg = _get_settings()
    registry = _get_registry()
    service = OllamaLocalModelService(cfg, registry)

    async def _pull():
        try:
            await service.pull_model(model)
        except Exception as exc:
            _LOG.warning("拉取本地模型失败: %s", exc)

    asyncio.ensure_future(_pull())
    return jsonify({"status": "pulling", "model": model})
