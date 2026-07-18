"""ToolEdit — 编辑文件工具

为什么做：AI 需要局部修改文件，无需重写全量内容。
实现方法：从旧 tools.py tool_edit_file 提取，支持 old_str→new_str 替换。

TODO: P1 按 Aider 方案升级，支持模糊匹配 + AST 对齐 + git checkpoint 回滚
层&依赖：infrastructure.tools.file 层，依赖 pathlib
"""

from __future__ import annotations

from pathlib import Path

from flypig.infrastructure.tools.registry import tool


@tool(name="edit_file", category="file", description="Edit a specific part of a file")
class ToolEdit:
    """编辑文件（old_str → new_str 替换）"""

    def __init__(self, workspace_dir: Path | None) -> None:
        self.workspace_dir = workspace_dir

    async def __call__(self, path: str, old_str: str, new_str: str) -> str:
        ws_msg = self._check_workspace()
        if ws_msg:
            return ws_msg

        file_path = self._resolve(path)
        if not file_path.exists():
            return f"Error: File not found: {file_path}"

        content = file_path.read_text(encoding="utf-8")
        if old_str not in content:
            return "Error: String not found in file"

        new_content = content.replace(old_str, new_str, 1)
        file_path.write_text(new_content, encoding="utf-8")
        return f"Successfully edited {file_path}"

    def _check_workspace(self) -> str | None:
        if self.workspace_dir is None or not str(self.workspace_dir):
            return "请先选择工作区后再操作。"
        return None

    def _resolve(self, path_str: str) -> Path:
        p = Path(path_str)
        if p.is_absolute():
            return p
        if self.workspace_dir is None:
            return p
        return self.workspace_dir / p
