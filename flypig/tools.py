"""工具执行器"""
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional
from .context_compressor import TreeSitterCompressor


class ToolExecutor:
    """执行各种工具操作"""
    
    def __init__(self, workspace_dir: str = None):
        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            self.workspace_dir = Path.cwd()
        self.is_windows = platform.system() == "Windows" or os.name == "nt"
        self.is_vscode = os.environ.get('TERM_PROGRAM', '') == 'vscode'
        self.compressor = TreeSitterCompressor()
    
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
                ['uname', '-r'], capture_output=True, text=True, timeout=2
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
                    capture_output=True, text=True, timeout=2
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
        """执行 shell 命令"""
        command = args.get("command", "")
        timeout_val = args.get("timeout", 60)

        if not command:
            return "Error: No command provided"

        # Windows 命令转换
        if self.is_windows:
            command = self._convert_windows_command(command)

        try:
            # ── VS Code 终端：开新 IDE 标签页 ──
            if self.is_vscode:
                ok, msg = self._open_vscode_terminal(command)
                if ok:
                    return msg
                # 失败则回退到下一种方式

            # ── Windows：新终端窗口 ──
            if self.is_windows:
                try:
                    # 自动检测当前 Shell：PowerShell 还是 cmd
                    if os.environ.get('PSModulePath'):
                        shell_name = "powershell"
                        start_cmd = (
                            f'start "FlyPig" powershell -NoExit -Command '
                            f'"cd \'{self.workspace_dir}\'; {command}"'
                        )
                    else:
                        shell_name = "cmd"
                        start_cmd = (
                            f'start "FlyPig" cmd /k '
                            f'"cd /d {self.workspace_dir} & {command}"'
                        )
                    subprocess.Popen(start_cmd, shell=True)
                    return f"[Started in new {shell_name} window] {command}"
                except Exception as e:
                    return f"[error starting] {e}"

            # ── Linux/Mac：开新终端窗口或后台运行 ──
            success, msg = self._open_new_terminal_linux(command)
            if success:
                return msg
            # 即使后台运行也返回，不阻塞
            return msg

        except Exception as e:
            return f"[error] {e}"

    
    def _convert_windows_command(self, command: str) -> str:
        """转换 Linux 命令到 Windows"""
        cmd = command.strip().lower()
        
        # ls 命令
        if cmd.startswith("ls ") or cmd.startswith("ls\n"):
            parts = command.split(None, 1)
            if len(parts) > 1:
                return "dir " + parts[1].replace("/", "\\")
            return "dir"
        
        if cmd == "ls":
            return "dir"
        
        # cat 命令
        if cmd.startswith("cat "):
            parts = command.split(None, 1)
            if len(parts) > 1:
                return "type " + parts[1].replace("/", "\\")
        
        # find 命令
        if cmd.startswith("find "):
            return command  # 复杂命令直接返回，让它失败
        
        return command
    
    def tool_find_files(self, args: Dict) -> str:
        """查找文件"""
        pattern = args.get("pattern", "*")
        path_str = args.get("path", ".")
        
        # 解析路径
        search_path = self._resolve_path(path_str)
        
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
            
            return "\n".join(rel_files) if rel_files else "No files found"
            
        except Exception as e:
            return f"Error: {e}"
    
    def tool_grep(self, args: Dict) -> str:
        """搜索文件内容"""
        pattern = args.get("pattern", "")
        path_str = args.get("path", ".")
        
        if not pattern:
            return "Error: No pattern provided"
        
        search_path = self._resolve_path(path_str)
        
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
                    "description": f"Execute a shell command on {platform.system()}",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Shell command to execute"},
                            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 60}
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
