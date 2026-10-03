"""config_helpers — 配置路由的路径/最近工作区辅助函数

为什么做：config_routes 同时承担 REST 路由与路径标准化、最近工作区读写，
         职责过多；把可独立测试的纯逻辑抽出来，路由文件只保留 HTTP 编排。
实现方法：JSON 文件读写（最近工作区）+ 跨平台路径标准化 + 去重合并。
层&依赖：interface.rest.routes 层，被 config_routes 依赖
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 最近工作区记录文件（与 config_routes 同级，路径深度保持一致）
RECENT_FILE = (
    Path(__file__).resolve().parent.parent.parent / "flypig" / "data" / "recent_workspaces.json"
)
MAX_RECENT = 8
_JSON_INDENT = 2


def load_recent() -> list[str]:
    """读取最近工作区列表（文件不存在或解析失败时返回空列表）"""
    if not RECENT_FILE.exists():
        return []
    try:
        with open(RECENT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_recent(workspaces: list[str]) -> None:
    """写入最近工作区列表"""
    RECENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RECENT_FILE, "w", encoding="utf-8") as f:
        json.dump(workspaces, f, ensure_ascii=False, indent=_JSON_INDENT)


def normalize_path(raw: str) -> str:
    """统一路径：根据运行环境自动转换路径格式

    - Windows 上：`C:\\foo` → `C:\\foo`（保持原样）
    - Linux/WSL 上：`C:\\foo` → `/mnt/c/foo`，`/mnt/c/foo` 保留原样

    返回 Path.resolve() 后的绝对路径，可直接比较是否指向同一目录。
    """
    if sys.platform == "win32":
        return raw

    raw = raw.strip().replace("\\", "/").rstrip("/")
    # 用切片判断（长度不足时切片为空串，不会 IndexError）
    if raw[1:2] == ":":
        drive, rest = raw.split(":", 1)
        raw = f"/mnt/{drive.lower()}/{rest.lstrip('/')}"

    # 用 Path.resolve() 消除多层嵌套垃圾（如 /mnt/c/x/C:/y/...）
    # Path 在 Linux 上看到 C:/ 会视为相对路径，resolve() 会塌缩到 ./
    try:
        return str(Path(raw).resolve())
    except Exception:
        return raw


def merge_recent_workspaces(recent: list[str], current: str) -> list[str]:
    """把当前工作区并入历史记录：标准化去重 + 置顶 + 截断"""
    seen: set[str] = {normalize_path(current)}
    cleaned: list[str] = [current]
    for item in recent:
        item_norm = normalize_path(item)
        # 跳过指向不存在目录的旧垃圾条目
        try:
            if not Path(item_norm).exists():
                continue
        except Exception:
            continue
        if item_norm in seen:
            continue
        seen.add(item_norm)
        cleaned.append(item)
    return cleaned[:MAX_RECENT]
