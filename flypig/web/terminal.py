"""Web 终端 — PTY 会话管理 (WebSocket 桥接)"""

import os
import platform
import threading
import time
from typing import Optional


class TerminalSession:
    """单个终端 PTY 会话 — 桥接 xterm.js <-> 本地 shell"""

    def __init__(self, sid: str, workspace_dir: str = None, on_output=None):
        self.sid = sid
        self.workspace_dir = workspace_dir or os.getcwd()
        self._on_output = on_output  # callback: (sid, data) -> None
        self._process = None  # pywinpty.PtyProcess or None
        self._reader_thread: Optional[threading.Thread] = None
        self._alive = False
        self._lock = threading.Lock()

    def start(self):
        """启动 shell 进程"""
        if self._alive:
            return
        ok = self._start_pty()
        if not ok:
            return
        self._alive = True
        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True,
            name=f"pty-reader-{self.sid}"
        )
        self._reader_thread.start()

    def _start_pty(self) -> bool:
        """启动 PTY 进程"""
        if platform.system() == "Windows":
            return self._start_windows()
        else:
            return self._start_unix()

    def _start_windows(self) -> bool:
        """Windows: 使用 pywinpty"""
        try:
            import pywinpty
        except ImportError:
            return False
        try:
            shell = "powershell.exe -NoProfile -NoLogo"
            self._process = pywinpty.PtyProcess.spawn(
                shell, cwd=self.workspace_dir, cols=80, rows=24,
            )
            # 禁用鼠标追踪 + 设置 UTF-8 编码
            self._process.write(
                "\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l"
                "\r\n"
            )
            return True
        except Exception:
            return False

    def _start_unix(self) -> bool:
        """Unix: 使用 pty.fork()"""
        try:
            import pty
            import struct
            import termios
            import fcntl
            import signal
        except ImportError:
            return False
        try:
            pid, fd = pty.fork()
            if pid == 0:
                # 子进程
                shell = os.environ.get("SHELL", "/bin/bash")
                if self.workspace_dir:
                    os.chdir(self.workspace_dir)
                os.execvp(shell, [shell])
                os._exit(1)
            self._pid = pid
            self._fd = fd
            # 启用 reader 读取
            self._unix_fd = fd
            return True
        except Exception:
            return False

    def _reader_loop(self):
        """后台线程: 从 PTY 读取输出并回调"""
        try:
            while self._alive:
                data = self._read_pty()
                if data:
                    if self._on_output:
                        self._on_output(self.sid, data)
                else:
                    time.sleep(0.01)
        except (EOFError, OSError, RuntimeError):
            pass
        finally:
            self._alive = False

    def _read_pty(self) -> str:
        """从 PTY 读取数据"""
        if platform.system() == "Windows":
            if self._process:
                try:
                    return self._process.read(4096)
                except Exception:
                    return ""
        else:
            if hasattr(self, '_unix_fd') and self._unix_fd >= 0:
                try:
                    data = os.read(self._unix_fd, 4096)
                    if data:
                        return data.decode("utf-8", errors="replace")
                    raise EOFError("PTY closed")
                except BlockingIOError:
                    return ""
                except OSError:
                    raise EOFError("PTY closed")
        return ""

    def write(self, data: str):
        """写入 PTY stdin（来自用户键盘）"""
        if not self._alive:
            return
        with self._lock:
            if platform.system() == "Windows" and self._process:
                self._process.write(data)
            elif hasattr(self, '_unix_fd') and self._unix_fd >= 0:
                os.write(self._unix_fd, data.encode("utf-8"))

    def resize(self, cols: int, rows: int):
        """调整终端大小"""
        if platform.system() == "Windows":
            if self._process:
                try:
                    self._process.set_size(cols, rows)
                except Exception:
                    pass
        else:
            if hasattr(self, '_unix_fd') and self._unix_fd >= 0:
                try:
                    import struct, termios, fcntl
                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    fcntl.ioctl(self._unix_fd, termios.TIOCSWINSZ, winsize)
                except Exception:
                    pass

    def stop(self):
        """停止 shell 进程"""
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
            if hasattr(self, '_unix_fd') and self._unix_fd >= 0:
                try:
                    os.close(self._unix_fd)
                except Exception:
                    pass
                self._unix_fd = -1

    def is_alive(self) -> bool:
        return self._alive

    def __del__(self):
        self.stop()
