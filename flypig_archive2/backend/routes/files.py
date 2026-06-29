"""文件操作路由 (/api/tree /api/file)

为什么做：前端文件树和编辑器需要通过 API 读取文件内容和目录结构。
实现方法：/api/tree POST 列出目录内容，/api/file GET 读取文件内容。
实现效果：前端文件树自动展开/刷新，编辑器实时加载文件内容。
技术栈：Quart, pathlib

层&依赖：backend.routes 层，依赖本地文件系统
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点
"""

from pathlib import Path
from quart import Blueprint, request, jsonify

files_bp = Blueprint("files", __name__)


@files_bp.route("/api/tree", methods=["POST"])
async def tree():
    """返回指定路径下的目录树（1 层深，前端懒加载）"""
    data = await request.get_json(force=True)
    path_str = (data or {}).get("path", "")
    if not path_str:
        return jsonify({"error": "path required"}), 400

    p = Path(path_str).resolve()
    if not p.exists() or not p.is_dir():
        return jsonify({"error": "目录不存在", "path": str(p)}), 404

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

    return jsonify({
        "path": str(p),
        "entries": entries,
    })


@files_bp.route("/api/file", methods=["GET"])
async def read_file():
    """读取文件内容"""
    file_path = request.args.get("path", "")
    if not file_path:
        return jsonify({"error": "path required"}), 400

    p = Path(file_path).resolve()
    if not p.exists() or not p.is_file():
        return jsonify({"error": "文件不存在", "path": str(p)}), 404

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        return jsonify({
            "path": str(p),
            "name": p.name,
            "content": content,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
