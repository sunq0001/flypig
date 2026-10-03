"""ToolGrep — 文件内容搜索工具

为什么做：AI 需要按文本模式搜索文件内容。
实现方法：先尝试 ripgrep（rg）命令行工具，失败则降级为纯 Python 逐文件搜索。

改进 vs 旧 tools.py：
- 旧代码用 rglob("*") 逐个 read_text() 搜索，大项目极慢
- 新代码优先用 ripgrep（比 Python 快 10-100 倍），无 rg 时降级
- 不再用裸 except:

层&依赖：infrastructure.tools.search 层
"""

from __future__ import annotations

import asyncio
import fnmatch
from pathlib import Path

from flypig.infrastructure.tools.registry import tool

# 返回结果上限（条数 / 单行截断字符数）
_MAX_MATCHES = 50
_MAX_MATCH_CHARS = 200


@tool(name="grep", category="search", description="Search for text patterns in files")
class ToolGrep:
    """搜索文件内容"""

    def __init__(self, workspace_dir: Path) -> None:
        self.workspace_dir = workspace_dir

    async def __call__(self, pattern: str, glob: str = "*.py", path: str = ".") -> str:
        try:
            search_path = self._resolve(path)

            # 优先用 ripgrep
            result = await self._try_ripgrep(pattern, glob, search_path)
            if result is not None:
                return result

            # 降级：纯 Python fallback
            return await self._python_grep(pattern, glob, search_path)
        except Exception as e:
            return f"[Error] grep 执行失败: {e}"

    async def _try_ripgrep(self, pattern: str, glob: str, path: Path) -> str | None:
        try:
            proc = await asyncio.create_subprocess_exec(
                "rg",
                "--no-heading",
                "--line-number",
                f"--glob={glob}",
                pattern,
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            out = stdout.decode("utf-8", errors="replace").strip()
            if out:
                return out
            return f"No matches for '{pattern}'"
        except (TimeoutError, FileNotFoundError):
            return None

    async def _python_grep(self, pattern: str, glob: str, path: Path) -> str:
        matches: list[str] = []
        for file_path in path.rglob("*"):
            if not (file_path.is_file() and fnmatch.fnmatch(file_path.name, glob)):
                continue
            matches.extend(self._scan_file(file_path, pattern))

        if not matches:
            return f"No matches for '{pattern}'"
        return "\n".join(matches[:_MAX_MATCHES])

    def _scan_file(self, file_path: Path, pattern: str) -> list[str]:
        """扫描单个文件，返回匹配行（相对路径:行号:内容）"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        found: list[str] = []
        for i, line in enumerate(content.splitlines(), 1):
            if pattern in line:
                rel = file_path.relative_to(self.workspace_dir)
                found.append(f"{rel}:{i}:{line.strip()[:_MAX_MATCH_CHARS]}")
        return found

    def _resolve(self, path_str: str) -> Path:
        p = Path(path_str)
        if p.is_absolute():
            return p
        return self.workspace_dir / p
