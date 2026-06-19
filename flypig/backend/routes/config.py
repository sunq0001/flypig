"""配置路由 (/api/config/*)

为什么做：前端从单一端点获取所有配置，避免硬编码默认值。
前端 POST 修改配置（工作区、API Key）持久化到 config.yaml。

实现方法：Quart Blueprint，通过 app.config["flypig_config"] 访问 Config 实例。
- GET /api/config → 返回完整配置对象
- POST /api/config/workspace → 设置工作区路径
- POST /api/config/apikey → 保存 API Key

技术栈：Quart, Blueprint, Config

注意事项：
- GET /api/config 返回 workspace 为 null → 前端显示 InitWizard（选工作区）
- GET /api/config 返回了 workspace → 前端直接进聊天界面
- 前端不硬编码任何默认值，全部从此端点读取
- 无 API Key 不阻止向导流程，用户在聊天界面发送消息时才拦截弹窗
- POST /api/config/workspace 若目录不存在则自动创建
- POST /api/config/apikey 按 provider 保存，同一个提供商只存一个 Key
"""

from pathlib import Path

from quart import Blueprint, current_app, jsonify, request

config_bp = Blueprint("config", __name__, url_prefix="/api/config")


def _get_config():
    return current_app.config["flypig_config"]


@config_bp.route("", methods=["GET"])
async def get_config():
    cfg = _get_config()
    return jsonify(cfg.to_frontend())


@config_bp.route("/workspace", methods=["POST"])
async def set_workspace():
    data = await request.get_json(force=True)
    path = (data or {}).get("path", "")
    if not path:
        return jsonify({"error": "path required"}), 400

    p = Path(path).resolve()
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)

    cfg = _get_config()
    cfg.set_workspace(str(p))
    return jsonify({"workspace": str(p)})


@config_bp.route("/apikey", methods=["POST"])
async def save_apikey():
    data = await request.get_json(force=True)
    provider = (data or {}).get("provider", "")
    api_key = (data or {}).get("api_key", "")
    if not provider or not api_key:
        return jsonify({"error": "provider and api_key required"}), 400

    cfg = _get_config()
    cfg.save_api_key(provider, api_key)
    return jsonify({"ok": True})


@config_bp.route("/browse", methods=["POST"])
async def browse():
    """浏览指定路径下的目录内容"""
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

    return jsonify({
        "path": str(p),
        "parent": str(p.parent) if p.parent != p else None,
        "entries": entries,
    })


@config_bp.route("/mkdir", methods=["POST"])
async def mkdir():
    """在指定路径下创建新目录"""
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
