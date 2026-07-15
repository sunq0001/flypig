"""config_routes

为什么做：前端需要获取/修改应用配置（工作目录、API Key、本地模型等）

实现方法：REST 路由组：workspace/apikey/browse/mkdir/local-models/local-models/pull

层&依赖：interface.rest.routes 层
"""

from __future__ import annotations

import asyncio
import json
import sys
from http import HTTPStatus
from pathlib import Path

from loguru import logger
from quart import Blueprint, current_app, jsonify, request

from flypig.domain.registry import ModelRegistry
from flypig.infrastructure.ollama.service import OllamaLocalModelService

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
    for meta in registry.all_models.values():
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
            "recent_workspaces": _load_recent(),
        }
    )


@config_bp.route("", methods=["PUT"])
async def update_config():
    data = await request.get_json(force=True) or {}
    cfg = _get_settings()
    if "default_model" in data:
        cfg.default_model = data["default_model"]
    return jsonify({"ok": True})


_RECENT_FILE = Path(__file__).resolve().parent.parent.parent / "flypig" / "data" / "recent_workspaces.json"
_MAX_RECENT = 8


def _load_recent() -> list[str]:
    if not _RECENT_FILE.exists():
        return []
    try:
        with open(_RECENT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_recent(workspaces: list[str]) -> None:
    _RECENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_RECENT_FILE, "w", encoding="utf-8") as f:
        json.dump(workspaces, f, ensure_ascii=False, indent=2)


def _normalize_path(raw: str) -> str:
    """统一路径：根据运行环境自动转换路径格式

    - Windows 上：`C:\foo` → `C:\foo`（保持原样）
    - Linux/WSL 上：`C:\foo` → `/mnt/c/foo`，`/mnt/c/foo` 保留原样

    返回 Path.resolve() 后的绝对路径，可直接比较是否指向同一目录。
    """
    if sys.platform == "win32":
        return raw

    raw = raw.strip().replace("\\", "/").rstrip("/")
    if len(raw) >= 2 and raw[1] == ":":
        drive = raw[0].lower()
        rest = raw[3:] if raw[2] in "/\\" else raw[2:]
        raw = f"/mnt/{drive}/{rest}"

    # 用 Path.resolve() 消除多层嵌套垃圾（如 /mnt/c/x/C:/y/...）
    # Path 在 Linux 上看到 C:/ 会视为相对路径，resolve() 会塌缩到 ./
    try:
        return str(Path(raw).resolve())
    except Exception:
        return raw


@config_bp.route("/workspace", methods=["POST"])
async def set_workspace() -> dict:  # type: ignore[misc]
    data = await request.get_json(force=True)
    path = (data or {}).get("path", "")
    if not path:
        return jsonify({"error": "path required"}), HTTPStatus.BAD_REQUEST

    # 统一转 WSL 路径（Linux 下 C:\ 不被视为绝对路径）
    converted = _normalize_path(path)
    p = Path(converted).resolve()
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)

    cfg = _get_settings()
    cfg.workspace = str(p)

    # 更新最近工作区（去重 + 移到最前 + 截断）
    recent = _load_recent()
    # 标准化所有旧条目 + 当前路径，路径相同的视为重复
    normalized_p = _normalize_path(str(p))
    seen: set[str] = {normalized_p}
    cleaned: list[str] = [str(p)]
    for r in recent:
        r_norm = _normalize_path(r)
        # 跳过指向不存在目录的旧垃圾条目
        try:
            if not Path(r_norm).exists():
                continue
        except Exception:
            continue
        if r_norm in seen:
            continue
        seen.add(r_norm)
        cleaned.append(r)
    _save_recent(cleaned[:_MAX_RECENT])

    return jsonify({"workspace": str(p)})


@config_bp.route("/workspace/recent", methods=["DELETE"])
async def clear_recent():
    """清除最近工作区记录"""
    _save_recent([])
    return jsonify({"ok": True})


@config_bp.route("/apikey", methods=["POST"])
async def save_apikey() -> dict:  # type: ignore[misc]
    data = await request.get_json(force=True)
    provider = (data or {}).get("provider", "")
    api_key = (data or {}).get("api_key", "")
    if not provider or not api_key:
        return jsonify({"error": "provider and api_key required"}), HTTPStatus.BAD_REQUEST

    container = current_app.config.get("flypig_container")
    if not container:
        return jsonify({"error": "服务未就绪"}), HTTPStatus.INTERNAL_SERVER_ERROR

    service = container.api_key_service()
    result = await service.validate_and_save(provider, api_key)

    if not result.valid:
        return jsonify({"error": result.message}), HTTPStatus.BAD_REQUEST

    # 同步到内存 settings（供当前请求后续使用）
    registry: ModelRegistry = _get_registry()
    attr = registry.provider_key_map.get(provider, "")
    if attr:
        cfg = _get_settings()
        if hasattr(cfg, attr):
            setattr(cfg, attr, api_key)

    return jsonify({"ok": True, "message": result.message})


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
async def pull_local_model():  # type: ignore[misc]
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
            logger.warning("拉取本地模型失败: %s", exc)

    asyncio.ensure_future(_pull())
    return jsonify({"status": "pulling", "model": model})
