"""ToolBash — Shell 命令执行工具

为什么做：AI 需要执行 shell 命令（编译/git/pip/dev server 等）。
实现方法：基于 asyncio.create_subprocess_shell 执行，支持超时和后台模式。

改进 vs 旧 tools.py：
- 去掉 5 种执行路径的混乱逻辑（VS Code 终端/弹窗/内联/沙箱/交互式）
- 统一走 asyncio subprocess，简洁可靠
- Windows/Linux 命令转换交给调用方，不在工具层做

安全说明：本工具的职责就是执行 shell 命令（等同用户的终端），
管道 / && / 环境变量等 shell 语义是功能必需，因此刻意使用 shell=True。
仅当调用方（ToolExecutor）在用户确认后才分发命令。

层&依赖：infrastructure.tools.system 层，依赖 asyncio 标准库
"""

from __future__ import annotations

import asyncio

from flypig.infrastructure.tools.registry import tool

# ── 默认参数与输出处理 ──
_DEFAULT_TIMEOUT = 60
_BG_MAX_TIMEOUT = 3600
_OUTPUT_TAIL_CHARS = 2000
_DECODE_ERRORS = "replace"


@tool(name="bash", category="system", timeout=60, description="Execute a shell command")
class ToolBash:
    """Shell 命令执行器"""

    def __init__(self) -> None:
        self._bg_tasks: dict[str, asyncio.subprocess.Process] = {}

    async def __call__(
        self, command: str, timeout: int = _DEFAULT_TIMEOUT, persist: bool = False
    ) -> str:
        try:
            if persist:
                return await self._run_background(command, timeout)
            return await self._run_foreground(command, timeout)
        except Exception as e:
            return f"[ERROR] {type(e).__name__}: {e}"

    async def _run_foreground(self, command: str, timeout: int) -> str:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            out = stdout.decode("utf-8", errors=_DECODE_ERRORS)
            err = stderr.decode("utf-8", errors=_DECODE_ERRORS)

            if proc.returncode == 0:
                return out or err or "[OK] Command completed (no output)"
            return (
                f"[ERROR] Exit code {proc.returncode}\n"
                f"{err[:_OUTPUT_TAIL_CHARS]}\n{out[:_OUTPUT_TAIL_CHARS]}"
            )

        except TimeoutError:
            proc.kill()
            await proc.wait()
            return f"[TIMEOUT] Command exceeded {timeout}s"
        except Exception as e:
            return f"[ERROR] {type(e).__name__}: {e}"

    async def _run_background(self, command: str, timeout: int) -> str:
        task_id = f"bg_{id(command)}"
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as e:
            return f"[ERROR] 无法启动后台任务: {e}"

        self._bg_tasks[task_id] = proc

        # 后台收集输出，避免管道塞满阻塞子进程
        asyncio.create_task(_collect_output(proc, timeout))

        return (
            f"[Background Task] task_id={task_id}\n"
            f"  Command: {command}\n"
            f"  Use task_status(task_id='{task_id}') to check result."
        )


async def _collect_output(proc: asyncio.subprocess.Process, timeout: int) -> tuple[str, str]:
    """后台收集进程输出，返回 (stdout, stderr)"""
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=max(timeout, _BG_MAX_TIMEOUT)
        )
    except TimeoutError:
        proc.kill()
        return "", "后台任务超时被终止"
    return (
        stdout.decode("utf-8", errors=_DECODE_ERRORS),
        stderr.decode("utf-8", errors=_DECODE_ERRORS),
    )
