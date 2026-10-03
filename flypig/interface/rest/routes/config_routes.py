"""config_routes

为什么做：前端需要获取/修改应用配置（工作目录、API Key、本地模型等）

实现方法：REST 路由组：workspace/apikey/browse/mkdir/local-models/pull
         路径标准化与最近工作区读写见 config_helpers.py

层&依赖：interface.rest.routes 层
"""

from __future__ import annotations

import asyncio
from http import HTTPStatus
from pathlib import Path

from loguru import logger
from quart import Blueprint, Response, current_app, jsonify, request

from flypig.domain.registry import ModelRegistry
from flypig.infrastructure.ollama.service import OllamaLocalModelService

# 同层辅助模块用相对导入（避免被跨包依赖统计计为第三个层）
from .config_helpers import (
    load_recent,
    merge_recent_workspaces,
    normalize_path,
    save_recent,
)

HTTP_BAD_REQUEST = 400
COLOR_KEY = "color"
DISPLAY_NAME_KEY = "display_name"
ICON_KEY = "icon"

# ── HTTP 方法名 ──
_METHOD_GET = "GET"
_METHOD_POST = "POST"
_METHOD_PUT = "PUT"
_METHOD_DELETE = "DELETE"

# ── 请求/响应 JSON 字段名 ──
KEY_ERROR = "error"
KEY_PATH = "path"
KEY_NAME = "name"
KEY_OK = "ok"
KEY_PARENT = "parent"
KEY_PROVIDER = "provider"
KEY_API_KEY = "api_key"
DEFAULT_MODEL_KEY = "default_model"

config_bp = Blueprint("config", __name__, url_prefix="/api/config")


def _get_settings():
    return current_app.config["flypig_settings"]


def _get_registry() -> ModelRegistry:
    return current_app.config["flypig_model_registry"]


def _build_providers() -> dict:
    """从注册表重建厂商元数据字典（前端需要 icon/color/display_name）"""
    registry = _get_registry()
    providers: dict[str, dict] = {}
    for meta in registry.all_models.values():
        provider = meta.get(KEY_PROVIDER, "")
        if not provider or provider in providers:
            continue
        providers[provider] = {
            ICON_KEY: meta.get(ICON_KEY, ""),
            COLOR_KEY: meta.get(COLOR_KEY, ""),
            DISPLAY_NAME_KEY: meta.get(DISPLAY_NAME_KEY, ""),
        }
    # 本地厂商来自 JSON local 段
    local = registry.get_local_config()
    providers[local.get(KEY_PROVIDER, "Local")] = {
        ICON_KEY: local.get(ICON_KEY, "mdi:laptop"),
        COLOR_KEY: local.get(COLOR_KEY, "#888"),
        DISPLAY_NAME_KEY: local.get(DISPLAY_NAME_KEY, "本地"),
    }
    return providers


@config_bp.route("", methods=[_METHOD_GET])
async def get_config() -> Response:
    cfg = _get_settings()
    registry = _get_registry()

    models = []
    for name in registry.known_models():
        meta = registry.resolve(name)
        if meta is None:
            continue
        provider = meta[KEY_PROVIDER]
        attr = registry.provider_key_map.get(provider, "")
        has_key = bool(getattr(cfg, attr, None))
        models.append(
            {
                KEY_NAME: name,
                KEY_PROVIDER: provider,
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
            DEFAULT_MODEL_KEY: cfg.default_model,
            "workspace": cfg.workspace,
            "log_level": cfg.log_level,
            "models": models,
            "providers": _build_providers(),
            "recent_workspaces": load_recent(),
        }
    )


@config_bp.route("", methods=[_METHOD_PUT])
async def update_config() -> Response:
    data = await request.get_json(force=True) or {}
    cfg = _get_settings()
    if DEFAULT_MODEL_KEY in data:
        cfg.default_model = data[DEFAULT_MODEL_KEY]
    return jsonify({KEY_OK: True})


@config_bp.route("/workspace", methods=[_METHOD_POST])
async def set_workspace() -> Response | tuple[Response, int]:  # type: ignore[misc]
    data = await request.get_json(force=True)
    path = (data or {}).get(KEY_PATH, "")
    if not path:
        return jsonify({KEY_ERROR: "path required"}), HTTPStatus.BAD_REQUEST

    # 统一转 WSL 路径（Linux 下 C:\ 不被视为绝对路径）
    converted = normalize_path(path)
    p = Path(converted).resolve()
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)

    cfg = _get_settings()
    cfg.workspace = str(p)

    # 更新最近工作区（去重 + 移到最前 + 截断）
    save_recent(merge_recent_workspaces(load_recent(), str(p)))

    return jsonify({"workspace": str(p)})


@config_bp.route("/workspace/recent", methods=[_METHOD_DELETE])
async def clear_recent() -> Response:
    """清除最近工作区记录"""
    save_recent([])
    return jsonify({KEY_OK: True})


@config_bp.route("/apikey", methods=[_METHOD_POST])
async def save_apikey() -> Response | tuple[Response, int]:  # type: ignore[misc]
    data = await request.get_json(force=True)
    provider = (data or {}).get(KEY_PROVIDER, "")
    api_key = (data or {}).get(KEY_API_KEY, "")
    if not provider or not api_key:
        return jsonify({KEY_ERROR: "provider and api_key required"}), HTTPStatus.BAD_REQUEST

    container = current_app.config.get("flypig_container")
    if not container:
        return jsonify({KEY_ERROR: "服务未就绪"}), HTTPStatus.INTERNAL_SERVER_ERROR

    service = container.api_key_service()
    result = await service.validate_and_save(provider, api_key)

    if not result.valid:
        return jsonify({KEY_ERROR: result.message}), HTTPStatus.BAD_REQUEST

    # 同步到内存 settings（供当前请求后续使用）
    registry: ModelRegistry = _get_registry()
    attr = registry.provider_key_map.get(provider, "")
    if attr:
        cfg = _get_settings()
        if hasattr(cfg, attr):
            setattr(cfg, attr, api_key)

    return jsonify({KEY_OK: True, "message": result.message})


@config_bp.route("/browse", methods=[_METHOD_POST])
async def browse() -> Response | tuple[Response, int]:
    data = await request.get_json(force=True)
    path = (data or {}).get(KEY_PATH, ".")
    p = Path(path).resolve()

    if not p.exists() or not p.is_dir():
        return jsonify({KEY_ERROR: "目录不存在", KEY_PATH: str(p)}), HTTPStatus.NOT_FOUND

    entries = []
    try:
        for entry in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                entries.append(
                    {
                        KEY_NAME: entry.name,
                        "type": "directory" if entry.is_dir() else "file",
                    }
                )
            except PermissionError:
                continue
    except PermissionError:
        return jsonify({KEY_ERROR: "无权限访问", KEY_PATH: str(p)}), HTTPStatus.FORBIDDEN

    return jsonify(
        {
            KEY_PATH: str(p),
            KEY_PARENT: str(p.parent) if p.parent != p else None,
            "entries": entries,
        }
    )


@config_bp.route("/mkdir", methods=[_METHOD_POST])
async def mkdir() -> Response | tuple[Response, int]:
    data = await request.get_json(force=True)
    parent = (data or {}).get(KEY_PARENT, "")
    name = (data or {}).get(KEY_NAME, "")
    if not parent or not name:
        return jsonify({KEY_ERROR: "parent and name required"}), HTTPStatus.BAD_REQUEST
    p = Path(parent).resolve() / name
    try:
        p.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        return jsonify({KEY_ERROR: "无权限创建目录"}), HTTPStatus.FORBIDDEN
    return jsonify({KEY_PATH: str(p), KEY_NAME: name})


# ── 本地模型引导 ──


@config_bp.route("/local-models", methods=[_METHOD_GET])
async def get_local_models() -> Response:
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


@config_bp.route("/local-models/pull", methods=[_METHOD_POST])
async def pull_local_model() -> Response | tuple[Response, int]:  # type: ignore[misc]
    data = await request.get_json(force=True) or {}
    model = data.get("model", "")
    if not model:
        return jsonify({KEY_ERROR: "model required"}), HTTP_BAD_REQUEST

    cfg = _get_settings()
    registry = _get_registry()
    service = OllamaLocalModelService(cfg, registry)

    async def _pull() -> None:
        try:
            await service.pull_model(model)
        except Exception as exc:
            logger.warning("拉取本地模型失败: %s", exc)

    asyncio.ensure_future(_pull())
    return jsonify({"status": "pulling", "model": model})
