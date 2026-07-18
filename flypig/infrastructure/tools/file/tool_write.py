"""ToolWrite — 写文件工具

为什么做：AI 创建/覆盖文件，工作区未设置时提示先选择。
实现方法：@tool 注册，自动创建父目录，工作区检查。

层&依赖：infrastructure.tools.file 层，依赖 pathlib
"""

from __future__ import annotations

from pathlib import Path

from flypig.infrastructure.tools.registry import tool


@tool(name="write_file", category="file", description="Create or overwrite a file with content")
class ToolWrite:
    """写入文件"""

    def __init__(self, workspace_dir: Path | None) -> None:
        self.workspace_dir = workspace_dir

    async def __call__(self, path: str, content: str) -> str:
        ws_msg = self._check_workspace()
        if ws_msg:
            return ws_msg

        file_path = self._resolve(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote to {file_path}"

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
