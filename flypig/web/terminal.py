"""Web 终端 — asyncio PTY 终端管理 (WebSocket 字节管道)

架构：
  ┌─ xterm.js ─┬── WS(字节) ──┬─ asyncio server ──┬─ PTY ──┬─ Shell
  │            │              │  port 8322         │        │
  └────────────┘              └────────────────────┘        └────────
"""

import os
import platform
import threading
from typing import Optional


class Terminal:
    """单个 PTY 终端 — 与 Shell 进程的字节管道"""

    def __init__(self, term_id: str, cwd: Optional[str] = None):
        self.term_id = term_id
        # 验证 cwd 存在，不存在则使用 CWD
        raw_cwd = cwd or os.getcwd()
        self.cwd = raw_cwd if os.path.isdir(raw_cwd) else os.getcwd()
        self._process = None
        self._alive = False
        self._lock = threading.Lock()
        self.shell_name = self._detect_shell()

    def _detect_shell(self) -> str:
        if platform.system() == "Windows":
            return "PowerShell"
        return os.environ.get("SHELL", "bash")

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
        # pywinpty 兼容两种模块名：pip 版(pywinpty / 3.0.3+) / conda 版(winpty / 3.0.2)
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
            shell = "powershell.exe -NoProfile -NoLogo"
            print(f"  [PTY] 启动 PowerShell (via {pty_mod.__name__}): cwd={self.cwd}")
            # 兼容不同版本的 spawn 参数
            spawn_kwargs = {"cwd": self.cwd}
            import inspect
            sig = inspect.signature(pty_mod.PtyProcess.spawn)
            if "dimensions" in sig.parameters:
                spawn_kwargs["dimensions"] = (24, 80)
            else:
                spawn_kwargs["cols"] = 80
                spawn_kwargs["rows"] = 24
            self._process = pty_mod.PtyProcess.spawn(shell, **spawn_kwargs)
            print(f"  [PTY] PowerShell 已启动")
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
                # 子进程
                shell = os.environ.get("SHELL", "/bin/bash")
                if self.cwd:
                    os.chdir(self.cwd)
                os.execvp(shell, [shell])
                os._exit(1)
            self._pid = pid
            self._fd = fd
            return True
        except Exception:
            return False

    def read(self, size: int = 4096) -> Optional[bytes]:
        """从 PTY 读取输出（阻塞调用，应在 executor 中执行）

        Returns:
            bytes: 输出数据
            b"": 暂时无数据，可重试
            None: PTY 已关闭（不可恢复）
        """
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
                if hasattr(self, '_fd') and self._fd >= 0:
                    data = os.read(self._fd, size)
                    return data if data else None  # EOF
                return None
        except RuntimeError:
            # pywinpty: 暂时无数据可读，不是终端挂了
            return b""
        except (EOFError, OSError):
            self._alive = False
            return None

    def write(self, data: bytes):
        """写入 PTY stdin"""
        if not self._alive:
            return
        with self._lock:
            try:
                if platform.system() == "Windows" and self._process:
                    text = data.decode("utf-8", errors="replace")
                    self._process.write(text)
                elif hasattr(self, '_fd') and self._fd >= 0:
                    os.write(self._fd, data)
            except (OSError, RuntimeError):
                self._alive = False

    def resize(self, cols: int, rows: int):
        """调整终端大小"""
        if platform.system() == "Windows":
            if self._process:
                try:
                    self._process.set_size(cols, rows)
                except Exception:
                    pass
        else:
            if hasattr(self, '_fd') and self._fd >= 0:
                try:
                    import struct
                    import termios
                    import fcntl
                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    fcntl.ioctl(self._fd, termios.TIOCSWINSZ, winsize)
                except Exception:
                    pass

    def destroy(self):
        """停止并清理 PTY 进程"""
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
                if hasattr(self, '_pid') and self._pid > 0:
                    try:
                        import signal
                        os.kill(self._pid, signal.SIGTERM)
                        os.waitpid(self._pid, 0)
                    except Exception:
                        pass
                    self._pid = -1
                if hasattr(self, '_fd') and self._fd >= 0:
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

    def create(self, term_id: str, cwd: Optional[str] = None) -> Terminal:
        """创建并注册一个新终端"""
        term = Terminal(term_id, cwd)
        term.create()
        with self._lock:
            self._terminals[term_id] = term
        return term

    def get(self, term_id: str) -> Optional[Terminal]:
        with self._lock:
            return self._terminals.get(term_id)

    def destroy(self, term_id: str):
        """销毁终端"""
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
        """销毁所有终端"""
        with self._lock:
            terms = list(self._terminals.values())
            self._terminals.clear()
        for t in terms:
            t.destroy()
