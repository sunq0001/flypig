"""ToolFindFiles — 文件查找工具

为什么做：AI 需要按文件名模式搜索文件。
实现方法：基于 Path.glob/rglob，支持通配符模式。

层&依赖：infrastructure.tools.search 层，依赖 pathlib
"""

from __future__ import annotations

from pathlib import Path

from flypig.infrastructure.tools.registry import tool


@tool(name="find_files", category="search", description="Find files by name pattern")
class ToolFindFiles:
    """查找文件"""

    def __init__(self, workspace_dir: Path) -> None:
        self.workspace_dir = workspace_dir

    async def __call__(self, pattern: str, path: str = ".") -> str:
        search_path = self._resolve(path)

        if "*" in pattern or "?" in pattern:
            files = list(search_path.glob(pattern))
        else:
            files = list(search_path.rglob(pattern))

        if not files:
            files = list(self.workspace_dir.rglob(pattern))

        if not files:
            return "No files found"

        rels = []
        for f in files[:50]:
            if f.is_file():
                try:
                    rels.append(str(f.relative_to(self.workspace_dir)))
                except ValueError:
                    rels.append(str(f))

        return "\n".join(rels) if rels else "No files found"

    def _resolve(self, path_str: str) -> Path:
        p = Path(path_str)
        if p.is_absolute():
            return p
        return self.workspace_dir / p
