"""文件操作路由 (/api/tree /api/file)

层&amp;依赖：interface.rest.routes 层，依赖本地文件系统
"""

from http import HTTPStatus
from pathlib import Path
from quart import Blueprint, request, jsonify

files_bp = Blueprint("files", __name__)


@files_bp.route("/api/tree", methods=["POST"])
async def tree():
    data = await request.get_json(force=True)
    path_str = (data or {}).get("path", "")
    if not path_str:
        return jsonify({"error": "path required"}), HTTPStatus.BAD_REQUEST

    p = Path(path_str).resolve()
    if not p.exists() or not p.is_dir():
        return jsonify({"error": "目录不存在", "path": str(p)}), HTTPStatus.NOT_FOUND

    entries = []
    try:
        for entry in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if entry.name.startswith("."):
                continue
            try:
                is_dir = entry.is_dir()
                entries.append({
                    "name": entry.name,
                    "path": str(entry.resolve()),
                    "type": "directory" if is_dir else "file",
                })
            except (PermissionError, OSError):
                continue
    except PermissionError:
        return jsonify({"error": "无权限访问", "path": str(p)}), 403

    return jsonify({"path": str(p), "entries": entries})


@files_bp.route("/api/file", methods=["GET"])
async def read_file():
    file_path = request.args.get("path", "")
    if not file_path:
        return jsonify({"error": "path required"}), 400

    p = Path(file_path).resolve()
    if not p.exists() or not p.is_file():
        return jsonify({"error": "文件不存在", "path": str(p)}), 404

    # 图片文件返回原始二进制
    image_exts = {'.png','.jpg','.jpeg','.gif','.svg','.webp','.ico','.bmp'}
    if p.suffix.lower() in image_exts:
        from quart import send_file
        return await send_file(str(p), mimetype=f"image/{p.suffix[1:].lower()}")

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        return jsonify({"path": str(p), "name": p.name, "content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
