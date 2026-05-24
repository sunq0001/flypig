"""工具执行器"""
import asyncio
import os
import platform
import subprocess
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional
from .background import BackgroundTaskManager
from .context_compressor import TreeSitterCompressor


# ── ANSI escape sequences 清理 ──
_ANSI_ESC = re.compile(
    # Windows DSR mouse (ESC [[<...M/m) — 先匹配更精确的
    r'\x1b\[\[[<][0-?]*[Mm]'
    # CSI sequences (ESC [... )
    r'|\x1b\[[0-?]*[ -/]*[@-~]'
    # 控制字符 (保留 \t\n\r)
    r'|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]'
    # C1 控制字符
    r'|[\x80-\x9f]'
    # 其他 ESC + 1 字符
    r'|\x1b.'
)

# 残留序列清理（\x1b 已被 strip 但留下 [[<35;1;0M 文本）
_ANSI_FRAGMENT = re.compile(
    r'\[\[<\d+(?:;\d+)*[Mm]'       # DSR 鼠标残留 [[<...M/m
    r'|\[\[\d+(?:;\d+)*[A-Za-z]'    # 其他 [[... 残留
    r'|\[\d+(?:;\d+)*[A-Za-z]'      # 更短变种 [... 残留
    r'|<Objs[^>]*>'                 # CLIXML 标签头
    r'|</?[A-Z][A-Za-z0-9_.]*[^>]*>'  # 其他 XML 标签
    r'|[\r\n]+'                      # 多余空行压缩（保留一个）
)

def strip_ansi(text: str) -> str:
    """移除 ANSI escape sequences + 清理残留的控制序列片段"""
    t = _ANSI_ESC.sub('', text)
    t = _ANSI_FRAGMENT.sub('', t)
    # 压缩连续空行
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()



class ToolExecutor:
    """执行各种工具操作"""

    def __init__(self, workspace_dir: str = None, path_validator=None, sandbox_manager=None):
        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            self.workspace_dir = Path.cwd()
        self.is_windows = platform.system() == "Windows" or os.name == "nt"
        self.is_vscode = os.environ.get('TERM_PROGRAM', '') == 'vscode'
        self.compressor = TreeSitterCompressor()
        self.path_validator = path_validator
        self.sandbox_manager = sandbox_manager
        self._web_mode = False  # Web UI 模式下内联执行命令
        self.bg_tasks = BackgroundTaskManager()  # 后台任务管理器

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """执行工具"""
        method = getattr(self, f"tool_{tool_name}", None)
        if method:
            return method(arguments)
        return f"Unknown tool: {tool_name}"
    
    def tool_read_file(self, args: Dict) -> str:
        """读取文件，可选项使用 Tree-sitter 上下文压缩"""
        file_path = self._resolve_path(args.get("path", ""))
        compress = args.get("compress", False)

        # 沙箱路径验证
        ok, err = self._validate_path(file_path, "read")
        if not ok:
            return err

        if not file_path.exists():
            return f"Error: File not found: {file_path}"

        try:
            content = file_path.read_text(encoding="utf-8")
            max_chars = args.get("max_chars", 50000)

            if compress:
                content = self.compressor.compress(
                    content, str(file_path), max_chars
                )

            if len(content) > max_chars:
                content = content[:max_chars] + f"\n... (truncated, total {len(content)} chars)"
            return content
        except Exception as e:
            return f"Error reading file: {e}"
    
    def tool_write_file(self, args: Dict) -> str:
        """写入文件"""
        file_path = self._resolve_path(args.get("path", ""))
        content = args.get("content", "")

        # 沙箱路径验证（写入模式）
        ok, err = self._validate_path(file_path, "write")
        if not ok:
            return err

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {e}"
    
    def tool_edit_file(self, args: Dict) -> str:
        """编辑文件"""
        file_path = self._resolve_path(args.get("path", ""))
        old_str = args.get("old_str", "")
        new_str = args.get("new_str", "")

        # 沙箱路径验证（写入模式）
        ok, err = self._validate_path(file_path, "write")
        if not ok:
            return err

        if not file_path.exists():
            return f"Error: File not found: {file_path}"
        
        try:
            content = file_path.read_text(encoding="utf-8")
            if old_str not in content:
                return f"Error: String not found"
            new_content = content.replace(old_str, new_str, 1)
            file_path.write_text(new_content, encoding="utf-8")
            return f"Successfully edited {file_path}"
        except Exception as e:
            return f"Error editing file: {e}"
    
    def _open_vscode_terminal(self, command: str) -> tuple:
        """在 VS Code 中打开新终端标签页，并写入临时脚本

        Returns: (success, message)
        """
        try:
            workspace = str(self.workspace_dir)

            # 创建临时脚本，新终端里只需 source 一下
            script_dir = Path("/tmp/flypig")
            script_dir.mkdir(parents=True, exist_ok=True)
            script_path = script_dir / f"cmd_{int(time.time())}.sh"
            script_path.write_text(
                f"#!/bin/bash\n"
                f"cd '{workspace}'\n"
                f"echo '>>> {command}'\n"
                f"{command}\n"
                f"echo ''\n"
                f"exec bash\n"
            )
            script_path.chmod(0o755)

            # 打开新 VS Code 终端标签页
            subprocess.Popen(
                ["code", "--command", "workbench.action.terminal.new"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True, (
                f"[VS Code 新终端已打开]\n"
                f"   命令: {command}\n"
                f"   在新终端中执行: source {script_path}"
            )
        except Exception as e:
            return False, str(e)

    def _is_wsl(self) -> bool:
        """检测是否在 WSL 中运行"""
        try:
            return 'microsoft' in subprocess.run(
                ['uname', '-r'], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=2
            ).stdout.lower()
        except Exception:
            return False

    def _open_new_terminal_linux(self, command: str) -> tuple:
        """在 Linux 环境打开新终端窗口运行命令
        
        Returns: (success, message)
        """
        workspace = str(self.workspace_dir)

        # 1) WSL → 用 cmd.exe 开新 Windows 终端窗口
        if self._is_wsl():
            try:
                win_path = subprocess.run(
                    ['wslpath', '-w', workspace],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=2
                ).stdout.strip()
                # 转义双引号
                safe_cmd = command.replace('"', '\\"')
                subprocess.Popen(
                    f'cmd.exe /c start "FlyPig" cmd /k "cd /d {win_path} & {safe_cmd}"',
                    shell=True
                )
                return True, f"[Started in new Windows terminal] {command}"
            except Exception:
                pass

        # 2) 桌面 Linux → 尝试各种终端模拟器
        terminals = [
            ("gnome-terminal",
             ["gnome-terminal", "--", "bash", "-c",
              f"cd '{workspace}' && {command}; echo; read -p '按 Enter 关闭...'"]),
            ("xterm",
             ["xterm", "-hold", "-e",
              f"cd '{workspace}' && {command}"]),
            ("konsole",
             ["konsole", "--hold", "-e",
              f"cd '{workspace}' && {command}"]),
            ("xfce4-terminal",
             ["xfce4-terminal", "--hold", "-e",
              f"cd '{workspace}' && {command}"]),
            ("lxterminal",
             ["lxterminal", "-e",
              f"cd '{workspace}' && {command}"]),
        ]

        for term_name, term_cmd in terminals:
            try:
                subprocess.run(["which", term_name],
                               capture_output=True, timeout=2)
                subprocess.Popen(term_cmd,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                return True, f"[Started in {term_name}] {command}"
            except Exception:
                continue

        # 3) 无 GUI 环境 (SSH 等) → 后台运行 + 日志文件
        log_path = f"/tmp/flypig_cmd_{int(time.time())}.log"
        bg_cmd = f"nohup bash -c 'cd {workspace} && {command}' > {log_path} 2>&1 &"
        subprocess.Popen(bg_cmd, shell=True)
        return False, f"[Running in background] {command}\n[Log] tail -f {log_path}"

    def tool_bash(self, args: Dict) -> str:
        """执行 shell 命令

        persist=False（默认）：通常命令，同步等待输出返回。
        persist=True：后台命令，立即返回 task_id，AI 可用 task_status/task_list 工具追踪。
        """
        command = args.get("command", "")
        timeout_val = args.get("timeout", 60)
        persist = args.get("persist", False)

        if not command:
            return "Error: No command provided"

        # ── persist=True：投递到后台任务管理器，立即返回 ──
        if persist:
            effective_timeout = max(timeout_val, 3600)
            task_id = self.bg_tasks.launch(command, timeout=effective_timeout)
            return (
                f"[Background Task] task_id={task_id}\n"
                f"  Command: {command}\n"
                f"  Use task_status(task_id='{task_id}') to check status.\n"
                f"  Use task_list() to see all background tasks."
            )

        # ── persist=False：同步等待输出 ──
        # Web UI 模式：内联执行
        if self._web_mode:
            return self._run_inline(command, timeout_val, persist=False)

        # 沙箱模式：在 Docker 容器内执行
        if self.sandbox_manager:
            workdir = "/workspace"
            return self.sandbox_manager.run_command(command, timeout_val, workdir)

        # 非沙箱模式
        if self.is_windows:
            command = self._convert_windows_command(command)

        try:
            # VS Code 终端
            if self.is_vscode:
                ok, msg = self._open_vscode_terminal(command)
                if ok:
                    return msg

            # Windows
            if self.is_windows:
                output = self._run_inline_windows(command, timeout_val)
                if output is not None:
                    return output
                return (
                    f"[INLINE TIMEOUT] Command exceeded {timeout_val}s: {command}\n"
                    f"  If this command needs an interactive terminal, "
                    f"retry with persist=True."
                )

            # Linux/Mac
            success, msg = self._open_new_terminal_linux(command)
            if success:
                return msg
            return msg

        except Exception as e:
            return f"[SYSTEM_ERROR] Tool internal exception ({type(e).__name__}): {e}"

    @staticmethod
    async def _run_subprocess_async_core(command: str, timeout_val: int) -> str:
        """async 子进程执行核心 — 使用 asyncio.create_subprocess_shell

        跨平台安全，Windows 上无管道死锁问题，支持 asyncio.wait_for 真实超时。

        Raises:
            asyncio.TimeoutError: 超时
        """
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_val
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise

        stdout_str = strip_ansi(stdout.decode("utf-8", errors="replace"))
        stderr_str = strip_ansi(stderr.decode("utf-8", errors="replace"))

        if proc.returncode == 0:
            if stdout_str:
                return stdout_str
            if stderr_str:
                return stderr_str
            return f"[OK] Command completed (no output): {command[:100]}"

        detail = stdout_str[:500] if stdout_str else ""
        if stderr_str:
            detail = (detail + "\n" + stderr_str[:500]).strip()
        return f"[ERROR] Exit code {proc.returncode}\n{detail[:2000]}"

    @staticmethod
    def _run_subprocess_sync(command: str, timeout_val: int) -> str:
        """同步包装层：用独立事件循环执行 async subprocess

        与 Agent 线程中的已有事件循环不冲突。
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                ToolExecutor._run_subprocess_async_core(command, timeout_val)
            )
        except asyncio.TimeoutError:
            return (
                f"[TIMEOUT] Command exceeded {timeout_val}s: {command[:100]}\n"
                f"  If this command needs an interactive terminal, "
                f"retry with persist=True."
            )
        except Exception as e:
            return f"[SYSTEM_ERROR] {type(e).__name__}: {e}"
        finally:
            loop.close()

    def _run_inline(self, command: str, timeout_val: int, persist: bool) -> str:
        """内联执行命令（Web/Headless 模式专用）

        使用 asyncio.create_subprocess_shell 异步执行，返回干净文本输出。
        persist=True 时使用更长超时（300s）。
        """
        effective_timeout = max(timeout_val, 300) if persist else timeout_val

        # ── 沙箱：走 docker exec ──
        if self.sandbox_manager:
            output = self.sandbox_manager.run_command(command, effective_timeout)
            return strip_ansi(output)

        # ── 无沙箱：走 asyncio subprocess ──
        return self._run_subprocess_sync(command, effective_timeout)

    
    @staticmethod
    def _should_run_inline(command: str) -> bool:
        """判断命令是否应该在当前进程内直接执行"""
        stripped = command.lstrip()
        if not stripped:
            return False
        first_word = stripped.split(None, 1)[0].lower()
        # 白名单命令：这些命令的 stdout 输出有价值，弹窗反而看不到
        inline_whitelist = {
            "dir", "type", "where", "echo", "cd", "git", "python", "pip",
            "node", "npm", "wsl", "powershell", "cmd", "findstr",
        }
        return first_word in inline_whitelist

    def _run_inline_windows(self, command: str, timeout_val: int) -> Optional[str]:
        """在当前进程内直接执行命令，捕获 stdout/stderr

        使用 asyncio.create_subprocess_shell，避免 Windows 管道死锁。
        输出已 strip ANSI escape sequences。

        Returns:
            str: 输出内容
            None: 执行失败（超时/系统错误），应由调用方回退到弹窗
        """
        output = self._run_subprocess_sync(command, timeout_val)
        if output.startswith("[TIMEOUT]") or output.startswith("[SYSTEM_ERROR]"):
            return None
        return output

    def _convert_windows_command(self, command: str) -> str:
        """转换 Linux 命令到 Windows（保持原格式，仅转换命令本身）"""
        # 只转换第一段命令单词，保留后面的参数
        stripped = command.lstrip()
        first_space = stripped.find(" ")
        first_word = stripped[:first_space] if first_space > 0 else stripped

        lower_word = first_word.lower()

        # ls → dir（移除不兼容的 flag）
        if lower_word in ("ls",):
            # 去掉 -la, -l, -a, -lh 等常见 Linux ls flags
            rest = stripped[len(first_word):].lstrip() if first_space > 0 else ""
            rest = self._strip_ls_flags(rest)
            return ("dir " + rest).rstrip()

        # cat → type
        if lower_word == "cat":
            rest = stripped[len(first_word):].lstrip() if first_space > 0 else ""
            return ("type " + rest).rstrip()

        # rm → del
        if lower_word == "rm":
            rest = stripped[len(first_word):].lstrip() if first_space > 0 else ""
            return ("del " + rest).rstrip()

        return command

    @staticmethod
    def _strip_ls_flags(args: str) -> str:
        """移除 ls 的 -la -l -a -lh 等 flags，保留路径参数"""
        parts = args.split()
        filtered = [p for p in parts if not p.startswith("-")]
        return " ".join(filtered)
    
    def tool_find_files(self, args: Dict) -> str:
        """查找文件"""
        pattern = args.get("pattern", "*")
        path_str = args.get("path", ".")
        
        # 解析路径
        search_path = self._resolve_path(path_str)

        # 沙箱路径验证（搜索目录也是一个读取操作）
        ok, err = self._validate_path(search_path, "read")
        if not ok:
            return err

        try:
            # 使用 glob 模式搜索
            if "*" in pattern or "?" in pattern:
                files = list(search_path.glob(pattern))
            else:
                # 简单文件名，递归搜索
                files = list(search_path.rglob(pattern))
            
            if not files:
                # 尝试在当前目录
                files = list(self.workspace_dir.rglob(pattern))
            
            if not files:
                return "No files found"
            
            # 返回相对路径
            rel_files = []
            for f in files[:50]:
                if f.is_file():
                    try:
                        rel = f.relative_to(self.workspace_dir)
                        rel_files.append(str(rel))
                    except ValueError:
                        rel_files.append(str(f))
            
            if not rel_files:
                return "No files found"

            result = f"[Search base: {search_path}]\n"
            result += "\n".join(rel_files)
            return result
            
        except Exception as e:
            return f"Error: {e}"
    
    def tool_grep(self, args: Dict) -> str:
        """搜索文件内容"""
        pattern = args.get("pattern", "")
        path_str = args.get("path", ".")
        
        if not pattern:
            return "Error: No pattern provided"
        
        search_path = self._resolve_path(path_str)

        # 沙箱路径验证
        ok, err = self._validate_path(search_path, "read")
        if not ok:
            return err

        try:
            matches = []
            for file_path in search_path.rglob("*"):
                if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.txt', '.md', '.yaml', '.yml', '.json', '.html', '.css', '.toml']:
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        if pattern in content:
                            matches.append(str(file_path.relative_to(search_path)))
                    except:
                        pass
            
            if not matches:
                return f"No files containing '{pattern}'"
            
            return "Found in:\n" + "\n".join(matches[:20])
        except Exception as e:
            return f"Error: {e}"
    
    @staticmethod
    def clear_pycache(target_dir: str = None):
        """清除目录下的所有 __pycache__ 缓存"""
        if target_dir:
            base = Path(target_dir)
        else:
            base = Path.cwd()

        count = 0
        for pyc in base.rglob("__pycache__"):
            try:
                import shutil
                shutil.rmtree(str(pyc))
                count += 1
            except Exception:
                pass
        return f"Cleared {count} __pycache__ directories"

    def tool_task_status(self, args: Dict) -> str:
        """查询后台任务的状态和输出"""
        task_id = args.get("task_id", "")
        if not task_id:
            tasks = self.bg_tasks.list_tasks()
            if not tasks:
                return "[Background Tasks] No active tasks."
            lines = ["[Background Tasks]"]
            for t in tasks:
                lines.append(
                    f"  [{t['status']}] {t['id']}  "
                    f"{t['command'][:80]}  "
                    f"({t['elapsed']:.1f}s)"
                )
            return "\n".join(lines)

        info = self.bg_tasks.status(task_id)
        if info is None:
            return f"[Error] Task not found: {task_id}"

        status_icon = {"running": ">", "completed": "OK",
                       "failed": "ERR", "timeout": "TO", "cancelled": "X"}
        icon = status_icon.get(info["status"], "?")

        lines = [
            f"[Background Task {info['id']}]",
            f"  Status: {icon} {info['status']}",
            f"  Command: {info['command']}",
            f"  Elapsed: {info['elapsed']}s",
        ]
        if info["exit_code"] is not None:
            lines.append(f"  Exit code: {info['exit_code']}")
        if info["output"]:
            lines.append(f"  Output:\n{info['output']}")
        return "\n".join(lines)

    def tool_task_list(self, args: Dict) -> str:
        """列出所有后台任务"""
        tasks = self.bg_tasks.list_tasks()
        if not tasks:
            return "[Background Tasks] No tasks."

        lines = ["[Background Tasks]"]
        for t in tasks:
            lines.append(
                f"  [{t['status']}] {t['id']}  "
                f"{t['command'][:80]}  "
                f"({t['elapsed']:.1f}s)"
            )
        lines.append(f"  ---\n  Total: {len(tasks)} task(s)")
        return "\n".join(lines)

    def _validate_path(self, path: Path, mode: str = "read") -> tuple:
        """验证路径是否允许访问（沙箱集成）

        Args:
            path: 已解析的 Path 对象
            mode: "read" | "write"

        Returns:
            (allowed: bool, error_message: str)
        """
        if not self.path_validator:
            return True, ""

        allowed, reason = self.path_validator.check_path(str(path), mode)
        if allowed:
            return True, ""

        # 拒绝 → 尝试运行时审批
        approval = self.path_validator.request_path_approval(str(path), mode)
        if approval == "allow":
            return True, ""
        elif approval == "allow_always":
            # 持久化到 config.yaml
            from .config import Config
            try:
                cfg = Config()
                cfg.save_sandbox_whitelist(str(path), mode)
            except Exception:
                pass
            return True, ""
        else:
            return False, f"[SECURITY] Path access denied: {path}"

    def _resolve_path(self, path_str: str) -> Path:
        """解析路径"""
        if not path_str or path_str == ".":
            return self.workspace_dir
        
        # 处理 Windows 绝对路径
        if len(path_str) > 1 and path_str[1] == ":":
            return Path(path_str)
        
        # 处理 Unix 绝对路径
        if path_str.startswith("/"):
            return Path(path_str)
        
        return self.workspace_dir / path_str
    
    def get_tools_schema(self) -> list:
        """获取工具定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the content of a file (with automatic context compression for large files)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path (absolute or relative to current directory)"},
                            "compress": {"type": "boolean", "description": "Enable Tree-sitter context compression to reduce token usage. Use compress=true when you only need an overview (function signatures + docstrings). Use compress=false (default) when you need the full implementation to edit or understand details.", "default": False}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Create or overwrite a file with content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                            "content": {"type": "string", "description": "File content"}
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Edit a specific part of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                            "old_str": {"type": "string", "description": "Content to replace"},
                            "new_str": {"type": "string", "description": "Replacement content"}
                        },
                        "required": ["path", "old_str", "new_str"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": "Execute a shell command. "
                                   "Short commands (compile, git, pip) return stdout directly. "
                                   "Long-running commands (npm run dev, python server) MUST use persist=true "
                                   "to run in the background without blocking your progress. "
                                   "You can then use task_status() to check output later. "
                                   "NOTE: The command appears as a card in the UI. "
                                   "The user can click '在新终端中执行' to run it in an interactive terminal.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Shell command to execute"},
                            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 60},
                            "persist": {"type": "boolean", "description": "Run in background (default: False). "
                                                                         "Use true for long-running commands like dev servers, npm install, docker builds.", "default": False}
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_files",
                    "description": "Find files by name pattern (supports wildcards like *.py)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "File pattern (e.g., calculator.py, *.py)"},
                            "path": {"type": "string", "description": "Directory to search", "default": "."}
                        },
                        "required": ["pattern"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "grep",
                    "description": "Search for text in files",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "Text pattern to search"},
                            "path": {"type": "string", "description": "Directory to search", "default": "."}
                        },
                        "required": ["pattern"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "task_status",
                    "description": "Check the status and output of a background task. "
                                   "Leave task_id empty to list all tasks.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Task ID to check, or empty to list all"}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "task_list",
                    "description": "List all background tasks with their status",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]
    