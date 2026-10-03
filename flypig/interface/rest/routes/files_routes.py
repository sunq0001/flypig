"""files_routes

为什么做：前端需要浏览文件树和读取文件内容

实现方法：POST /api/tree 返回目录结构，POST /api/file 读取文件内容

层&依赖：interface.rest.routes 层
"""

import asyncio
import re
import sys
from pathlib import Path

from quart import Blueprint, Response, jsonify, request, send_file

HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_FORBIDDEN = 403
HTTP_INTERNAL_SERVER_ERROR = 500
PATH_KEY = "path"
KEY_ERROR = "error"
NODE_TYPE_DIRECTORY = "directory"
NODE_TYPE_FILE = "file"

# Windows 盘符正则: 匹配 "C:\..." 或 "C:/..."
_WIN_DRIVE_RE = re.compile(r"^([A-Za-z]):[/\\]")

files_bp = Blueprint("files", __name__)


def _to_wsl_path(p: str) -> str:
    r"""转换路径格式：Windows 上保持原样，Linux/WSL 上将 C:\... 转为 /mnt/c/..."""
    if sys.platform == "win32":
        return p
    m = _WIN_DRIVE_RE.match(p)
    if m:
        return "/mnt/" + m.group(1).lower() + "/" + p[m.end() :].replace("\\", "/")
    return p


def _resolve_path(path_str: str) -> Path:
    """解析路径，自动转换 Windows 盘符为 WSL /mnt/ 路径"""
    return Path(_to_wsl_path(path_str)).resolve()


def _read_dir(p: Path) -> tuple[list[dict], int | None]:
    """读取目录条目（同步，供 asyncio.to_thread 调用）

    Returns:
        (条目列表, 错误状态码或 None)
    """
    if not p.exists() or not p.is_dir():
        return [], HTTP_NOT_FOUND

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
                        "type": NODE_TYPE_DIRECTORY if is_dir else NODE_TYPE_FILE,
                    }
                )
            except (PermissionError, OSError):
                continue
    except PermissionError:
        return [], HTTP_FORBIDDEN
    return entries, None


@files_bp.route("/api/tree", methods=["POST"])
async def tree() -> tuple[Response, int] | Response:
    data = await request.get_json(force=True)
    path_str = (data or {}).get(PATH_KEY, "")
    if not path_str:
        return jsonify({KEY_ERROR: "path required"}), HTTP_BAD_REQUEST

    p = _resolve_path(path_str)

    # 文件系统操作扔到线程池，避免阻塞事件循环（尤其 WSL /mnt/ 跨系统访问）
    entries, err_code = await asyncio.to_thread(_read_dir, p)
    if err_code:
        return jsonify({KEY_ERROR: "目录不存在"}), err_code

    return jsonify({PATH_KEY: str(p), "entries": entries})


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp"}


async def _send_image(p: Path) -> Response | tuple[Response, int]:
    """发送图片文件（原始二进制，不走 JSON）"""
    try:
        return await send_file(str(p), mimetype=f"image/{p.suffix[1:].lower()}")
    except Exception:
        return jsonify({KEY_ERROR: "读取图片失败"}), HTTP_INTERNAL_SERVER_ERROR


async def _read_text_file(p: Path) -> Response | tuple[Response, int]:
    """读取文本文件内容，失败时返回错误信息"""
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        return jsonify({PATH_KEY: str(p), "name": p.name, "content": content})
    except Exception as e:
        return jsonify({KEY_ERROR: str(e)}), HTTP_INTERNAL_SERVER_ERROR


@files_bp.route("/api/file", methods=["GET"])
async def read_file() -> Response | tuple[Response, int]:  # type: ignore[misc]
    file_path = request.args.get(PATH_KEY, "")
    if not file_path:
        return jsonify({KEY_ERROR: "path required"}), HTTP_BAD_REQUEST

    p = _resolve_path(file_path)
    if not p.exists() or not p.is_file():
        return jsonify({KEY_ERROR: "文件不存在", PATH_KEY: str(p)}), HTTP_NOT_FOUND

    if p.suffix.lower() in IMAGE_EXTENSIONS:
        return await _send_image(p)

    return await _read_text_file(p)
