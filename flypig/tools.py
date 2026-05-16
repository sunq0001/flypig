"""工具执行器"""
import os
import platform
import subprocess
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional
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

        沙箱模式双模式执行：
        - persist=True: spawn_command（非阻塞弹终端）
        - persist=False/不传: run_command（阻塞 docker exec 返回输出）

        Web UI 模式：始终内联执行，persist 仅表示更长超时（300s）
        """
        command = args.get("command", "")
        timeout_val = args.get("timeout", 60)
        persist = args.get("persist", False)

        if not command:
            return "Error: No command provided"

        # ── Web/Headless 模式：始终内联执行，不弹外部窗口 ──
        if self._web_mode:
            return self._run_inline(command, timeout_val, persist)

        # ── 沙箱模式：命令在 Docker 容器内执行 ──
        if self.sandbox_manager:
            workdir = "/workspace"  # 容器内固定挂载点
            if persist:
                return self.sandbox_manager.spawn_command(command, workdir)
            else:
                return self.sandbox_manager.run_command(command, timeout_val, workdir)

        # ── 非沙箱模式：保留原有行为 ──
        if self.is_windows:
            command = self._convert_windows_command(command)

        try:
            # ── VS Code 终端：开新 IDE 标签页 ──
            if self.is_vscode:
                ok, msg = self._open_vscode_terminal(command)
                if ok:
                    return msg

            # ── Windows ──
            if self.is_windows:
                if not persist:
                    output = self._run_inline_windows(command, timeout_val)
                    if output is not None:
                        return output
                    return (
                        f"[INLINE TIMEOUT] Command exceeded {timeout_val}s: {command}\n"
                        f"  If this command needs an interactive terminal, "
                        f"retry with persist=True."
                    )

                # persist=True → 弹新终端窗口
                workdir = str(self.workspace_dir)
                safe_cmd = command.replace("'", "''").replace("\n", " ")
                start_cmd = (
                    f'start "FlyPig" powershell -NoExit -Command '
                    f'"cd ''{workdir}''; {safe_cmd}"'
                )
                subprocess.Popen(
                    start_cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return f"[Started in new window] {command}"

            # ── Linux/Mac：开新终端窗口或后台运行 ──
            success, msg = self._open_new_terminal_linux(command)
            if success:
                return msg
            return msg

        except Exception as e:
            return f"[SYSTEM_ERROR] Tool internal exception ({type(e).__name__}): {e}"

    def _run_inline(self, command: str, timeout_val: int, persist: bool) -> str:
        """内联执行命令（Web/Headless 模式专用）

        简化的执行逻辑：使用 subprocess.run 执行并返回输出。
        persist=True 时使用更长超时（300s）。
        """
        effective_timeout = max(timeout_val, 300) if persist else timeout_val

        # ── 沙箱：走 docker exec，返回干净文本 ──
        if self.sandbox_manager:
            output = self.sandbox_manager.run_command(command, effective_timeout)
            return strip_ansi(output)

        # ── 无沙箱：走本地 subprocess ──
        effective_timeout = max(timeout_val, 300) if persist else timeout_val
        max_wait = effective_timeout
        check_interval = 3

        import threading as _threading
        result_holder = {"output": None, "exception": None}

        def _run():
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=max_wait,
                )
                raw_stdout = strip_ansi(result.stdout or "")
                raw_stderr = strip_ansi(result.stderr or "")
                if result.returncode == 0:
                    output = raw_stdout if raw_stdout else (raw_stderr if raw_stderr else "[OK] (no output)")
                else:
                    detail = raw_stdout[:500] if raw_stdout else ""
                    if raw_stderr:
                        detail = (detail + "\n" + raw_stderr[:500]).strip()
                    output = f"[ERROR] Exit code {result.returncode}\n{detail[:2000]}"
                result_holder["output"] = output
            except subprocess.TimeoutExpired:
                result_holder["exception"] = f"[INLINE TIMEOUT] {effective_timeout}s exceeded"
            except Exception as e:
                result_holder["exception"] = f"[SYSTEM_ERROR] {type(e).__name__}: {e}"

        t = _threading.Thread(target=_run, daemon=True)
        t.start()

        import time as time_module
        elapsed = 0
        while t.is_alive() and elapsed < effective_timeout:
            time_module.sleep(min(check_interval, effective_timeout - elapsed))
            elapsed += check_interval

        if result_holder["output"] is not None:
            return result_holder["output"]
        if result_holder["exception"]:
            return result_holder["exception"]

        return (
            f"[TIMEOUT] Command still running after {effective_timeout}s: {command[:100]}\n"
            f"  The command may be running in background. Check output manually."
        )

    
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

        输出已 strip ANSI escape sequences。

        Returns:
            str: 输出内容
            None: 执行失败，应由调用方回退到弹窗
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_val,
            )

            stdout = strip_ansi(result.stdout or "").strip()
            stderr = strip_ansi(result.stderr or "").strip()

            if result.returncode == 0:
                if stdout:
                    return stdout
                if stderr:
                    return stderr
                return f"[OK] Command completed (no output): {command[:100]}"

            detail = stdout[:200] if stdout else ""
            if stderr:
                detail = (detail + "\n" + stderr[:500]).strip()
            return f"[ERROR] Exit code {result.returncode}: {command[:100]}\n{detail[:1000]}"

        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None

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
                                   "Long-running commands (npm run dev, python server) need persist=true.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Shell command to execute"},
                            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 60},
                            "persist": {"type": "boolean", "description": "Keep terminal open (long-running commands like dev servers)", "default": False}
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
            }
        ]
