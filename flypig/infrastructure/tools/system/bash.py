"""ToolBash — Shell 命令执行工具

为什么做：AI 需要执行 shell 命令（编译/git/pip/dev server 等）。
实现方法：基于 asyncio.create_subprocess_shell 执行，支持超时和后台模式。

改进 vs 旧 tools.py：
- 去掉 5 种执行路径的混乱逻辑（VS Code 终端/弹窗/内联/沙箱/交互式）
- 统一走 asyncio subprocess，简洁可靠
- Windows/Linux 命令转换交给调用方，不在工具层做

层&依赖：infrastructure.tools.system 层，依赖 asyncio 标准库
"""

from __future__ import annotations

import asyncio

from flypig.infrastructure.tools.registry import tool


@tool(name="bash", category="system", timeout=60, description="Execute a shell command")
class ToolBash:
    """Shell 命令执行器"""

    def __init__(self) -> None:
        self._bg_tasks: dict[str, asyncio.subprocess.Process] = {}

    async def __call__(self, command: str, timeout: int = 60, persist: bool = False) -> str:
        if persist:
            return await self._run_background(command, timeout)
        return await self._run_foreground(command, timeout)

    async def _run_foreground(self, command: str, timeout: int) -> str:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            out = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")

            if proc.returncode == 0:
                return out or err or "[OK] Command completed (no output)"
            return f"[ERROR] Exit code {proc.returncode}\n{err[:2000]}\n{out[:2000]}"

        except TimeoutError:
            proc.kill()
            await proc.wait()
            return f"[TIMEOUT] Command exceeded {timeout}s"
        except Exception as e:
            return f"[ERROR] {type(e).__name__}: {e}"

    async def _run_background(self, command: str, timeout: int) -> str:
        task_id = f"bg_{id(command)}"
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._bg_tasks[task_id] = proc

        # 在后台收集输出
        async def _collect():
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=max(timeout, 3600))
            return stdout.decode("utf-8", errors="replace"), stderr.decode(
                "utf-8", errors="replace"
            )

        asyncio.create_task(_collect())
        self._bg_tasks[task_id] = proc

        return (
            f"[Background Task] task_id={task_id}\n"
            f"  Command: {command}\n"
            f"  Use task_status(task_id='{task_id}') to check result."
        )
