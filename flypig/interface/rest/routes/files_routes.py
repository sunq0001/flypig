"""files_routes

为什么做：前端需要浏览文件树和读取文件内容

实现方法：POST /api/tree 返回目录结构，POST /api/file 读取文件内容

层&依赖：interface.rest.routes 层
"""

import re
import sys
from http import HTTPStatus
from pathlib import Path

from quart import Blueprint, jsonify, request, send_file

HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_FORBIDDEN = 403
PATH_KEY = "path"

# Windows 盘符正则: 匹配 "C:\..." 或 "C:/..."
_WIN_DRIVE_RE = re.compile(r"^([A-Za-z]):[/\\]")

files_bp = Blueprint("files", __name__)


def _to_wsl_path(p: str) -> str:
    """转换路径格式：Windows 上保持原样，Linux/WSL 上将 C:\... 转为 /mnt/c/..."""
    if sys.platform == "win32":
        return p
    m = _WIN_DRIVE_RE.match(p)
    if m:
        return "/mnt/" + m.group(1).lower() + "/" + p[m.end() :].replace("\\", "/")
    return p


def _resolve_path(path_str: str) -> Path:
    """解析路径，自动转换 Windows 盘符为 WSL /mnt/ 路径"""
    return Path(_to_wsl_path(path_str)).resolve()


@files_bp.route("/api/tree", methods=["POST"])
async def tree():
    data = await request.get_json(force=True)
    path_str = (data or {}).get(PATH_KEY, "")
    if not path_str:
        return jsonify({"error": "path required"}), HTTPStatus.BAD_REQUEST

    p = _resolve_path(path_str)
    if not p.exists() or not p.is_dir():
        return jsonify({"error": "目录不存在", PATH_KEY: str(p)}), HTTPStatus.NOT_FOUND

    entries = []
    try:
        for entry in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if entry.name.startswith("."):
                continue
            try:
                is_dir = entry.is_dir()
                entries.append(
                    {
                        "name": entry.name,
                        PATH_KEY: str(entry.resolve()),
                        "type": "directory" if is_dir else "file",
                    }
                )
            except (PermissionError, OSError):
                continue
    except PermissionError:
        return jsonify({"error": "无权限访问", PATH_KEY: str(p)}), HTTP_FORBIDDEN

    return jsonify({PATH_KEY: str(p), "entries": entries})


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp"}


async def _send_image(p: Path):
    """发送图片文件（原始二进制，不走 JSON）"""
    try:
        return await send_file(str(p), mimetype=f"image/{p.suffix[1:].lower()}")
    except Exception:
        return jsonify({"error": "读取图片失败"}), 500


async def _read_text_file(p: Path):
    """读取文本文件内容，失败时返回错误信息"""
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        return jsonify({PATH_KEY: str(p), "name": p.name, "content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@files_bp.route("/api/file", methods=["GET"])
async def read_file():  # type: ignore[misc]
    file_path = request.args.get(PATH_KEY, "")
    if not file_path:
        return jsonify({"error": "path required"}), HTTP_BAD_REQUEST

    p = _resolve_path(file_path)
    if not p.exists() or not p.is_file():
        return jsonify({"error": "文件不存在", PATH_KEY: str(p)}), HTTP_NOT_FOUND

    if p.suffix.lower() in IMAGE_EXTENSIONS:
        return await _send_image(p)

    return await _read_text_file(p)
