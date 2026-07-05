"""Web 终端 — asyncio PTY 终端管理 (WebSocket 字节管道)

自动检测系统可用 shell，不可用时优雅降级到默认 shell。
用户无需手动安装任何额外软件。

架构：
  ┌─ xterm.js ─┬── WS(字节) ──┬─ asyncio server ──┬─ PTY ──┬─ Shell
  │            │              │  port 8322         │        │
  └────────────┘              └────────────────────┘        └────────
"""

import os
import platform
import shutil
import threading
from typing import Optional

# ─── Shell 配置 ────────────────────────────────────────────────

# Windows: shell 类型 → 可执行文件（按优先级列出多个可能路径）
SHELL_MAP_WIN = {
    "ps": ["powershell.exe", "pwsh.exe", "pwsh"],
    "bash": [
        "bash.exe",
        "C:\\Program Files\\Git\\bin\\bash.exe",
        "C:\\Program Files\\Git\\usr\\bin\\bash.exe",
    ],
    "zsh": ["zsh.exe"],
    "wsl": ["wsl.exe"],
}
# Unix: shell 类型 → 可执行路径
SHELL_MAP_UNIX = {
    "ps": ["pwsh", "powershell"],
    "bash": ["/bin/bash", "/usr/bin/bash"],
    "zsh": ["/bin/zsh", "/usr/bin/zsh"],
    "wsl": ["/bin/bash"],
}
SHELL_LABELS = {
    "ps": "PowerShell",
    "bash": "Bash",
    "zsh": "Zsh",
    "wsl": "WSL",
}
# 各 shell 启动参数
SHELL_ARGS = {
    "ps": "-NoProfile -NoLogo",
    "bash": "--login",
    "zsh": "",
    "wsl": "",
}
# 默认 fallback
_DEFAULT_SHELL = "ps"
_WIN_DEFAULT_CMD = "powershell.exe -NoProfile -NoLogo"


def detect_available_shells() -> dict:
    """检测系统上哪些 shell 可用，返回 { 'ps': True, 'bash': False, ... }"""
    shell_map = SHELL_MAP_WIN if platform.system() == "Windows" else SHELL_MAP_UNIX
    result = {}
    for shell_type, candidates in shell_map.items():
        found = False
        for exe in candidates:
            # 如果是绝对路径，检查文件存在；否则用 which 搜索 PATH
            if os.path.isabs(exe):
                found = os.path.isfile(exe)
            else:
                found = shutil.which(exe) is not None
            if found:
                break
        result[shell_type] = found
    return result


def resolve_shell_cmd(shell_type: str) -> str:
    """解析 shell 类型为可执行命令字符串，找不到则降级到默认"""
    shell_map = SHELL_MAP_WIN if platform.system() == "Windows" else SHELL_MAP_UNIX
    candidates = shell_map.get(shell_type, [])
    for exe in candidates:
        if os.path.isabs(exe):
            if os.path.isfile(exe):
                cmd = exe
                break
        else:
            found = shutil.which(exe)
            if found:
                cmd = found
                break
    else:
        # 全部找不到，降级到 PowerShell
        print(f"  [PTY] shell '{shell_type}' 不可用，降级到 PowerShell")
        if platform.system() == "Windows":
            return _WIN_DEFAULT_CMD
        return "/bin/bash"

    # 追加启动参数
    args = SHELL_ARGS.get(shell_type, "")
    if args:
        cmd = f"{cmd} {args}"
    print(f"  [PTY] 使用 shell: {shell_type} → {cmd}")
    return cmd


class Terminal:
    """单个 PTY 终端 — 与 Shell 进程的字节管道"""

    def __init__(self, term_id: str, cwd: Optional[str] = None, shell: str = "ps"):
        self.term_id = term_id
        raw_cwd = cwd or os.getcwd()
        self.cwd = raw_cwd if os.path.isdir(raw_cwd) else os.getcwd()
        self.shell = shell  # 'ps' | 'bash' | 'zsh' | 'wsl'
        self._process = None
        self._alive = False
        self._lock = threading.Lock()
        self.shell_name = SHELL_LABELS.get(shell, "PowerShell")

    def create(self) -> bool:
        """启动 PTY shell 进程"""
        with self._lock:
            if self._alive:
                return True
            ok = self._start_pty()
            if ok:
                self._alive = True
            return ok

    def _start_pty(self) -> bool:
        if platform.system() == "Windows":
            return self._start_windows()
        return self._start_unix()

    def _start_windows(self) -> bool:
        """Windows: 使用 pywinpty"""
        pty_mod = None
        for mod_name in ("pywinpty", "winpty"):
            try:
                pty_mod = __import__(mod_name)
                break
            except ImportError:
                continue
        if pty_mod is None:
            print("  [PTY] pywinpty/winpty 未安装")
            return False
        try:
            shell = resolve_shell_cmd(self.shell)
            print(
                f"  [PTY] 启动 {self.shell_name} (via {pty_mod.__name__}): cwd={self.cwd}"
            )
            spawn_kwargs = {"cwd": self.cwd}
            import inspect

            sig = inspect.signature(pty_mod.PtyProcess.spawn)
            if "dimensions" in sig.parameters:
                spawn_kwargs["dimensions"] = (24, 80)
            else:
                spawn_kwargs["cols"] = 80
                spawn_kwargs["rows"] = 24
            self._process = pty_mod.PtyProcess.spawn(shell, **spawn_kwargs)
            print(f"  [PTY] {self.shell_name} 已启动")
            return True
        except Exception as e:
            print(f"  [PTY] 启动失败: {e}")
            return False

    def _start_unix(self) -> bool:
        """Unix: 使用 pty.fork()"""
        try:
            import pty as pty_mod
            import struct
            import termios
            import fcntl
        except ImportError:
            return False
        try:
            pid, fd = pty_mod.fork()
            if pid == 0:
                shell = resolve_shell_cmd(self.shell)
                if self.cwd:
                    os.chdir(self.cwd)
                os.execvp(shell.split()[0], [shell])
                os._exit(1)
            self._pid = pid
            self._fd = fd
            return True
        except Exception:
            return False

    def read(self, size: int = 4096) -> Optional[bytes]:
        if not self._alive:
            return None
        try:
            if platform.system() == "Windows":
                if self._process:
                    data = self._process.read(size)
                    if isinstance(data, str):
                        return data.encode("utf-8", errors="replace")
                    return data
                return None
            else:
                if hasattr(self, "_fd") and self._fd >= 0:
                    data = os.read(self._fd, size)
                    return data if data else None
                return None
        except RuntimeError:
            return b""
        except (EOFError, OSError):
            self._alive = False
            return None

    def write(self, data: bytes):
        if not self._alive:
            return
        with self._lock:
            try:
                if platform.system() == "Windows" and self._process:
                    text = data.decode("utf-8", errors="replace")
                    self._process.write(text)
                elif hasattr(self, "_fd") and self._fd >= 0:
                    os.write(self._fd, data)
            except (OSError, RuntimeError):
                self._alive = False

    def resize(self, cols: int, rows: int):
        if platform.system() == "Windows":
            if self._process:
                try:
                    self._process.set_size(cols, rows)
                except Exception:
                    pass
        else:
            if hasattr(self, "_fd") and self._fd >= 0:
                try:
                    import struct
                    import termios
                    import fcntl

                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    fcntl.ioctl(self._fd, termios.TIOCSWINSZ, winsize)
                except Exception:
                    pass

    def destroy(self):
        with self._lock:
            self._alive = False
            if platform.system() == "Windows":
                if self._process:
                    try:
                        self._process.terminate()
                    except Exception:
                        pass
                    try:
                        self._process.close()
                    except Exception:
                        pass
                    self._process = None
            else:
                if hasattr(self, "_pid") and self._pid > 0:
                    try:
                        import signal

                        os.kill(self._pid, signal.SIGTERM)
                        os.waitpid(self._pid, 0)
                    except Exception:
                        pass
                    self._pid = -1
                if hasattr(self, "_fd") and self._fd >= 0:
                    try:
                        os.close(self._fd)
                    except Exception:
                        pass
                    self._fd = -1

    def is_alive(self) -> bool:
        return self._alive

    def __del__(self):
        self.destroy()

    def to_dict(self) -> dict:
        return {
            "term_id": self.term_id,
            "shell_name": self.shell_name,
            "alive": self._alive,
        }


class TerminalManager:
    """线程安全的终端管理器（Flask threading + asyncio WS 共享）"""

    def __init__(self):
        self._terminals: dict[str, Terminal] = {}
        self._lock = threading.Lock()

    def create(
        self, term_id: str, cwd: Optional[str] = None, shell: str = "ps"
    ) -> Terminal:
        """创建并注册一个新终端"""
        term = Terminal(term_id, cwd, shell)
        term.create()
        with self._lock:
            self._terminals[term_id] = term
        return term

    def get(self, term_id: str) -> Optional[Terminal]:
        with self._lock:
            return self._terminals.get(term_id)

    def destroy(self, term_id: str):
        with self._lock:
            term = self._terminals.pop(term_id, None)
        if term:
            term.destroy()

    def list(self) -> list[dict]:
        with self._lock:
            return [t.to_dict() for t in self._terminals.values()]

    def count(self) -> int:
        with self._lock:
            return len(self._terminals)

    def cleanup_all(self):
        with self._lock:
            terms = list(self._terminals.values())
            self._terminals.clear()
        for t in terms:
            t.destroy()
