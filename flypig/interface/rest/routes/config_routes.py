"""配置路由 (/api/config/*)

为什么做：前端从单一端点获取所有配置，避免硬编码默认值。
前端 POST 修改配置（工作区、API Key）持久化到 config.yaml。

层&依赖：interface.rest.routes 层，通过 ModelRegistry 依赖 domain
"""

from __future__ import annotations

import asyncio
from http import HTTPStatus
from pathlib import Path

from quart import Blueprint, current_app, jsonify, request

from flypig.domain.registry import ModelRegistry
from flypig.infrastructure.ollama.service import OllamaLocalModelService

config_bp = Blueprint("config", __name__, url_prefix="/api/config")


def _get_settings():
    return current_app.config["flypig_settings"]


def _get_registry() -> ModelRegistry:
    return current_app.config["flypig_model_registry"]


def _build_providers() -> dict:
    """从注册表重建厂商元数据字典（前端需要 icon/color/display_name）"""
    registry = _get_registry()
    providers: dict[str, dict] = {}
    for name, meta in registry.all_models.items():
        provider = meta.get("provider", "")
        if not provider or provider in providers:
            continue
        providers[provider] = {
            "icon": meta.get("icon", ""),
            "color": meta.get("color", ""),
            "display_name": meta.get("display_name", ""),
        }
    # 本地厂商来自 JSON local 段
    local = registry.get_local_config()
    providers[local.get("provider", "Local")] = {
        "icon": local.get("icon", "mdi:laptop"),
        "color": local.get("color", "#888"),
        "display_name": local.get("display_name", "本地"),
    }
    return providers


@config_bp.route("", methods=["GET"])
async def get_config():
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
        models.append({
            "name": name, "provider": provider,
            "base_url": meta.get("base_url", ""),
            "api_model": meta.get("api_model", ""),
            "local": False, "has_key": has_key,
        })
    # 本地模型通过 OllamaLocalModelService 动态获取
    local_service = OllamaLocalModelService(cfg, registry)
    models.extend(await local_service.list_models())

    return jsonify({
        "default_model": cfg.default_model,
        "workspace": cfg.workspace,
        "log_level": cfg.log_level,
        "models": models,
        "providers": _build_providers(),
    })


@config_bp.route("", methods=["PUT"])
async def update_config():
    data = await request.get_json(force=True) or {}
    cfg = _get_settings()
    if "default_model" in data:
        cfg.default_model = data["default_model"]
    return jsonify({"ok": True})


@config_bp.route("/workspace", methods=["POST"])
async def set_workspace():
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
async def save_apikey():
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
                entries.append({
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                })
            except PermissionError:
                continue
    except PermissionError:
        return jsonify({"error": "无权限访问", "path": str(p)}), HTTPStatus.FORBIDDEN

    return jsonify({"path": str(p), "parent": str(p.parent) if p.parent != p else None, "entries": entries})


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

    return jsonify({
        "running": ollama_running,
        "installed": installed,
        "ollama_base_url": cfg.ollama_base_url,
    })


@config_bp.route("/local-models/pull", methods=["POST"])
async def pull_local_model():
    data = await request.get_json(force=True) or {}
    model = data.get("model", "")
    if not model:
        return jsonify({"error": "model required"}), 400

    cfg = _get_settings()
    registry = _get_registry()
    service = OllamaLocalModelService(cfg, registry)

    async def _pull():
        await service.pull_model(model)

    asyncio.ensure_future(_pull())
    return jsonify({"status": "pulling", "model": model})
