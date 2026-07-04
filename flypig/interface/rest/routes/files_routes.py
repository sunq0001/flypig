"""files_routes

为什么做：前端需要浏览文件树和读取文件内容

实现方法：POST /api/tree 返回目录结构，POST /api/file 读取文件内容

层&依赖：interface.rest.routes 层
"""

from http import HTTPStatus
from pathlib import Path
from quart import Blueprint, request, Response, jsonify

files_bp = Blueprint("files", __name__)


@files_bp.route("/api/tree", methods=["POST"])
async def tree() -> dict:
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


IMAGE_EXTENSIONS = {'.png','.jpg','.jpeg','.gif','.svg','.webp','.ico','.bmp'}


async def _send_image(p: Path):
    """发送图片文件（原始二进制，不走 JSON）"""
    from quart import send_file
    return await send_file(str(p), mimetype=f"image/{p.suffix[1:].lower()}")


async def _read_text_file(p: Path):
    """读取文本文件内容，失败时返回错误信息"""
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        return jsonify({"path": str(p), "name": p.name, "content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@files_bp.route("/api/file", methods=["GET"])
async def read_file():  # type: ignore[misc]
    file_path = request.args.get("path", "")
    if not file_path:
        return jsonify({"error": "path required"}), 400

    p = Path(file_path).resolve()
    if not p.exists() or not p.is_file():
        return jsonify({"error": "文件不存在", "path": str(p)}), 404

    if p.suffix.lower() in IMAGE_EXTENSIONS:
        return await _send_image(p)

    return await _read_text_file(p)
