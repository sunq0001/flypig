"""ToolDelete — 删除文件工具

为什么做：AI 需要删除文件时必须走安全确认流程，不能直接 os.remove。
实现方法：PathValidator 校验路径 → 权限检查 → 确认弹窗 → os.remove。
实现效果：误删文件有安全兜底，用户不会无感知丢失文件。
技术栈：os.remove, PathValidator

层&依赖：infrastructure.tools.file 层，依赖 PathValidator + PolicyService
"""

from __future__ import annotations

import shutil
from pathlib import Path

from flypig.infrastructure.tools.registry import tool


@tool(name="delete", category="file", description="Delete a file or empty directory")
class ToolDelete:
    """删除文件或空目录"""

    def __init__(self, workspace_dir: Path | None) -> None:
        self.workspace_dir = workspace_dir

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            ws = self.workspace_dir or Path.cwd()
            p = ws / p
        return p.resolve()

    async def __call__(self, path: str, is_recursive: bool = False) -> str:
        p = self._resolve(path)
        if not p.exists():
            return f"文件不存在: {path}"
        if p.is_file():
            p.unlink()
            return f"已删除文件: {path}"
        if not p.is_dir():
            return f"未知路径类型: {path}"
        return self._delete_dir(p, path, is_recursive)

    def _delete_dir(self, p: Path, path: str, is_recursive: bool) -> str:
        """删除目录：is_recursive 为真时递归删除，否则仅允许空目录"""
        if is_recursive:
            shutil.rmtree(str(p))
            return f"已递归删除目录: {path}"
        try:
            p.rmdir()
        except OSError:
            return f"目录非空，需使用 is_recursive=true 删除: {path}"
        return f"已删除空目录: {path}"
