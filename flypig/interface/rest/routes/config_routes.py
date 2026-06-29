"""配置路由 (/api/config/*)

为什么做：前端从单一端点获取所有配置，避免硬编码默认值。
前端 POST 修改配置（工作区、API Key）持久化到 config.yaml。

层&amp;依赖：interface.rest.routes 层
"""

import asyncio
from pathlib import Path

from quart import Blueprint, current_app, jsonify, request

config_bp = Blueprint("config", __name__, url_prefix="/api/config")


def _get_settings():
    return current_app.config["flypig_settings"]


@config_bp.route("", methods=["GET"])
async def get_config():
    cfg = _get_settings()
    # 构建模型列表（注册表 + 本地）
    from flypig.domain.model_ref import known_models, resolve, get_local_models
    provider_key_map = {
        "DeepSeek": "deepseek_api_key", "OpenAI": "openai_api_key",
        "Anthropic": "anthropic_api_key", "Qwen": "qwen_api_key",
        "Tencent": "hunyuan_api_key", "ByteDance": "doubao_api_key",
        "Moonshot": "moonshot_api_key", "ZhipuAI": "zhipu_api_key",
    }
    models = []
    for name in known_models():
        meta = resolve(name)
        provider = meta["provider"]
        key_attr = provider_key_map.get(provider, "")
        has_key = bool(getattr(cfg, key_attr, None))
        models.append({
            "name": name, "provider": provider,
            "base_url": meta.get("base_url", ""),
            "api_model": meta.get("model", ""),
            "local": False, "has_key": has_key,
        })
    models.extend(get_local_models())
    return jsonify({
        "default_model": cfg.default_model,
        "workspace": cfg.workspace,
        "log_level": cfg.log_level,
        "models": models,
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
        return jsonify({"error": "path required"}), 400

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
        return jsonify({"error": "provider and api_key required"}), 400

    cfg = _get_settings()
    key_attr = f"{provider.lower()}_api_key"
    if hasattr(cfg, key_attr):
        setattr(cfg, key_attr, api_key)
    return jsonify({"ok": True})


@config_bp.route("/browse", methods=["POST"])
async def browse():
    data = await request.get_json(force=True)
    path = (data or {}).get("path", ".")
    p = Path(path).resolve()

    if not p.exists() or not p.is_dir():
        return jsonify({"error": "目录不存在", "path": str(p)}), 404

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
        return jsonify({"error": "无权限访问", "path": str(p)}), 403

    return jsonify({"path": str(p), "parent": str(p.parent) if p.parent != p else None, "entries": entries})


@config_bp.route("/mkdir", methods=["POST"])
async def mkdir():
    data = await request.get_json(force=True)
    parent = (data or {}).get("parent", "")
    name = (data or {}).get("name", "")
    if not parent or not name:
        return jsonify({"error": "parent and name required"}), 400
    p = Path(parent).resolve() / name
    try:
        p.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        return jsonify({"error": "无权限创建目录"}), 403
    return jsonify({"path": str(p), "name": name})


# ── 本地模型引导 ──
RECOMMENDED_LOCAL = [
    {"name": "qwen2.5:1.5b", "size": "~1.5GB", "description": "阿里通义千问 1.5B 轻量版"},
    {"name": "llama3.2:1b",  "size": "~700MB", "description": "Meta Llama 3.2 1B"},
    {"name": "phi3:mini",    "size": "~2.1GB", "description": "Microsoft Phi-3 Mini"},
]


@config_bp.route("/local-models", methods=["GET"])
async def get_local_models():
    installed = []
    ollama_running = False
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            ollama_running = True
            data = resp.json()
            installed = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        pass

    suggestions = [m for m in RECOMMENDED_LOCAL if m["name"] not in installed]

    return jsonify({"running": ollama_running, "installed": installed, "suggestions": suggestions})


@config_bp.route("/local-models/pull", methods=["POST"])
async def pull_local_model():
    data = await request.get_json(force=True) or {}
    model = data.get("model", "")
    if not model:
        return jsonify({"error": "model required"}), 400

    async def _pull():
        proc = await asyncio.create_subprocess_exec(
            "ollama", "pull", model,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        await proc.wait()

    asyncio.ensure_future(_pull())
    return jsonify({"status": "pulling", "model": model})
