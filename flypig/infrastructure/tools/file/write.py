"""ToolWrite — 写文件工具

为什么做：AI 创建/覆盖文件的基础能力。
实现方法：从旧 tools.py tool_write_file 提取，自动创建父目录。

层&依赖：infrastructure.tools.file 层，依赖 pathlib
"""

from __future__ import annotations

from pathlib import Path

from flypig.infrastructure.tools.registry import tool


@tool(name="write_file", category="file", description="Create or overwrite a file with content")
class ToolWrite:
    """写入文件"""

    def __init__(self, workspace_dir: Path) -> None:
        self.workspace_dir = workspace_dir

    async def __call__(self, path: str, content: str) -> str:
        file_path = self._resolve(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote to {file_path}"

    def _resolve(self, path_str: str) -> Path:
        p = Path(path_str)
        if p.is_absolute():
            return p
        return self.workspace_dir / p
