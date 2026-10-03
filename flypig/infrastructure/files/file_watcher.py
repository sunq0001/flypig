"""FileWatcher — 基于 watchdog 的跨平台文件变化监听

为什么做：AI 在本地创建/修改文件后，需要自动通知前端刷新文件树。
          之前在 FileTree 用 3s 轮询 I/O 开销太大，改用 OS 级事件监听。
实现方法：watchdog 根据平台自动选择：
          Windows → ReadDirectoryChangesW（内核级）
          Linux   → inotify（内核级）
          macOS   → FSEvents（内核级）
          检测到变化后放入全局 asyncio Queue，SSE 路由从中读取推送给前端。
层&依赖：infrastructure 层，依赖 watchdog + asyncio
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from threading import Thread

from watchdog.events import FileSystemEventHandler
from watchdog.observers.api import BaseObserver
from watchdog.observers.polling import PollingObserver

_log = logging.getLogger(__name__)

# 全局文件事件队列 — SSE 路由从此读取
file_event_queue: asyncio.Queue[str] = asyncio.Queue()


class _FileChangeHandler(FileSystemEventHandler):
    """watchdog 事件处理器"""

    def __init__(self) -> None:
        super().__init__()
        self._queue = file_event_queue

    def on_created(self, event) -> None:
        if not event.is_directory and not event.src_path.startswith("."):
            self._emit("created", event.src_path)

    def on_modified(self, event) -> None:
        if not event.is_directory and not event.src_path.startswith("."):
            self._emit("modified", event.src_path)

    def on_deleted(self, event) -> None:
        if not event.is_directory and not event.src_path.startswith("."):
            self._emit("deleted", event.src_path)

    def _emit(self, action: str, src_path: str) -> None:
        path = Path(src_path)
        if path.name.startswith(".") or path.suffix in (".pyc", ".swp", "~"):
            return
        _log.debug("[file_watcher] %s: %s", action, src_path)
        try:
            self._queue.put_nowait(f"{action}:{path.name}")
        except asyncio.QueueFull:
            # 队列满表示消费端（SSE）落后，丢弃本次事件是预期行为，但要留痕
            _log.warning("[file_watcher] 事件队列已满，丢弃: %s %s", action, path.name)


class FileWatcherService:
    """基于 watchdog 的文件变化监听服务"""

    def __init__(self, watch_dir: str | Path) -> None:
        self._watch_dir = Path(watch_dir).resolve()
        self._observer: BaseObserver | None = None
        self._thread: Thread | None = None

    def start(self) -> None:
        """启动文件监听

        优先用 PollingObserver（每 2 秒轮询），兼容 WSL /mnt/ 跨文件系统。
        如果 os 支持 inotify 且目录在原生 Linux 文件系统上，可改用 Observer 更高效。
        """
        if not self._watch_dir.exists():
            _log.warning("监听目录不存在: %s", self._watch_dir)
            return

        handler = _FileChangeHandler()
        self._observer = PollingObserver(timeout=1)
        self._observer.schedule(handler, str(self._watch_dir), recursive=True)
        self._observer.start()
        _log.info("文件监听已启动: %s (PollingObserver, 2s)", self._watch_dir)

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=3)
            _log.info("文件监听已停止")

    @property
    def is_alive(self) -> bool:
        return self._observer is not None and self._observer.is_alive()
