"""ToolRead — 读文件工具

为什么做：AI 需要读取文件内容，支持按行范围读取避免全量 token 消耗。
实现方法：从旧 tools.py tool_read_file 提取，支持 start/end 范围参数。

层&依赖：infrastructure.tools.file 层，依赖 pathlib
"""

from __future__ import annotations

from pathlib import Path

from flypig.infrastructure.tools.registry import tool


@tool(name="read_file", category="file", description="Read file content, optionally by line range")
class ToolRead:
    """读取文件内容，支持按行范围读取"""

    def __init__(self, workspace_dir: Path) -> None:
        self.workspace_dir = workspace_dir

    async def __call__(
        self,
        path: str,
        start: int | None = None,
        end: int | None = None,
        max_chars: int = 50000,
    ) -> str:
        file_path = self._resolve(path)
        if not file_path.exists():
            return f"Error: File not found: {file_path}"

        content = file_path.read_text(encoding="utf-8")

        if start is not None:
            lines = content.splitlines(keepends=True)
            content = "".join(lines[start - 1 : end])

        if len(content) > max_chars:
            content = content[:max_chars] + f"\n... (truncated, total {len(content)} chars)"

        return content

    def _resolve(self, path_str: str) -> Path:
        p = Path(path_str)
        if p.is_absolute():
            return p
        return self.workspace_dir / p
