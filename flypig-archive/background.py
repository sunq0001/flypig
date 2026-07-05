"""后台任务管理器 — AI 发射持久命令后立即继续工作

每个后台任务在独立线程 + 独立 asyncio 事件循环中运行。
通过任务 ID 追踪状态、检索输出、取消任务。
"""

import asyncio
import time
import threading
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Optional

# strip_ansi 在 tools.py 中定义，延迟导入避免循环引用


class TaskStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """单个后台任务的信息"""

    id: str
    command: str
    status: TaskStatus = TaskStatus.RUNNING
    output: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    start_time: float = 0.0
    end_time: Optional[float] = None
    error: Optional[str] = None
    timeout: int = 0
    _output_buf: str = ""  # 实时输出缓冲，每次回调后清空

    @property
    def elapsed(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def is_done(self) -> bool:
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.TIMEOUT,
            TaskStatus.CANCELLED,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "command": self.command[:200],
            "status": self.status.value,
            "output": self.output[-5000:],
            "exit_code": self.exit_code,
            "elapsed": round(self.elapsed, 2),
            "is_done": self.is_done,
        }

    def append_output(self, text: str):
        """追加输出到缓冲和总输出"""
        self._output_buf += text
        self.output += text

    def flush_output(self) -> str:
        """取出本次增量输出并清空缓冲"""
        buf = self._output_buf
        self._output_buf = ""
        return buf


class BackgroundTaskManager:
    """后台任务管理器

    用法:
        mgr = BackgroundTaskManager()
        task_id = mgr.launch("npm run dev", timeout=3600)
        info = mgr.status(task_id)
        output = mgr.get_output(task_id)
        list = mgr.list_tasks()
        mgr.cancel(task_id)
        mgr.cleanup_completed()
    """

    MAX_COMPLETED = 50

    def __init__(self, on_status_change: Optional[Callable[[TaskInfo], None]] = None):
        self._tasks: Dict[str, TaskInfo] = {}
        self._lock = threading.Lock()
        self._on_status_change = on_status_change
        self._stats = {"total_launched": 0, "total_completed": 0}

    # ── 公开 API ──

    def launch(self, command: str, timeout: int = 3600) -> str:
        """发射一个后台任务，立即返回 task_id

        Args:
            command: shell 命令
            timeout: 超时秒数

        Returns:
            task_id: 任务唯一标识
        """
        task_id = uuid.uuid4().hex[:12]

        info = TaskInfo(
            id=task_id,
            command=command,
            start_time=time.time(),
            timeout=timeout,
        )

        with self._lock:
            self._tasks[task_id] = info
            self._stats["total_launched"] += 1

        thread = threading.Thread(
            target=self._run_task,
            args=(task_id, command, timeout),
            daemon=True,
            name=f"bg-task-{task_id}",
        )
        thread.start()

        return task_id

    def status(self, task_id: str) -> Optional[dict]:
        """查询任务状态"""
        with self._lock:
            info = self._tasks.get(task_id)
            if info is None:
                return None
            return info.to_dict()

    def get_output(self, task_id: str) -> Optional[str]:
        """获取任务输出"""
        with self._lock:
            info = self._tasks.get(task_id)
            if info is None:
                return None
            return info.output

    def list_tasks(self) -> list[dict]:
        """列出所有未完成的活跃任务"""
        with self._lock:
            return [t.to_dict() for t in self._tasks.values()]

    def cancel(self, task_id: str) -> bool:
        """标记任务取消"""
        with self._lock:
            info = self._tasks.get(task_id)
            if info is None or info.is_done:
                return False
            info.status = TaskStatus.CANCELLED
            info.end_time = time.time()
            self._notify(info)
            return True

    def cleanup_completed(self):
        """清理已完成的任务（保留 MAX_COMPLETED 条记录）"""
        with self._lock:
            done = [t for t in self._tasks.values() if t.is_done]
            if len(done) <= self.MAX_COMPLETED:
                return
            # 按结束时间排序，删除最旧的
            done.sort(key=lambda t: t.end_time or 0)
            for t in done[: -self.MAX_COMPLETED]:
                self._tasks.pop(t.id, None)
            self._stats["total_completed"] += 1

    def stats(self) -> dict:
        return dict(self._stats)

    # ── 内部：任务执行 ──

    def _run_task(self, task_id: str, command: str, timeout: int):
        """在后台线程中执行 async subprocess"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._execute(task_id, command, timeout))
        except Exception as e:
            self._update_status(task_id, TaskStatus.FAILED, error=str(e))
        finally:
            loop.close()

    async def _execute(self, task_id: str, command: str, timeout: int):
        """async subprocess 执行逻辑"""
        info = self._get_info(task_id)
        if info is None:
            return

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def _read_stream(stream, is_stderr: bool):
            """逐行读取流并追加到输出缓冲"""
            from .tools import strip_ansi  # 延迟导入，避免循环引用

            while True:
                line = await stream.readline()
                if not line:
                    break
                text = strip_ansi(line.decode("utf-8", errors="replace"))
                if not text:
                    continue
                with self._lock:
                    info = self._tasks.get(task_id)
                    if info is None:
                        break
                    info.append_output(text + "\n")
                    if is_stderr:
                        info.stderr += text + "\n"
                    else:
                        info.stdout += text + "\n"
                    # 回调通知增量输出
                    if self._on_status_change:
                        try:
                            self._on_status_change(info)
                        except Exception:
                            pass

        try:
            # 并发读取 stdout 和 stderr
            await asyncio.wait_for(
                asyncio.gather(
                    _read_stream(proc.stdout, is_stderr=False),
                    _read_stream(proc.stderr, is_stderr=True),
                    proc.wait(),
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            self._update_status(task_id, TaskStatus.TIMEOUT, exit_code=-1)
            return

        if proc.returncode == 0:
            self._update_status(
                task_id, TaskStatus.COMPLETED, exit_code=proc.returncode
            )
        else:
            self._update_status(task_id, TaskStatus.FAILED, exit_code=proc.returncode)

    # ── 内部：状态管理 ──

    def _get_info(self, task_id: str) -> Optional[TaskInfo]:
        with self._lock:
            return self._tasks.get(task_id)

    def _update_status(
        self,
        task_id: str,
        status: TaskStatus,
        exit_code: Optional[int] = None,
        error: Optional[str] = None,
    ):
        with self._lock:
            info = self._tasks.get(task_id)
            if info is None:
                return
            info.status = status
            info.end_time = time.time()
            if exit_code is not None:
                info.exit_code = exit_code
            if error is not None:
                info.error = error
            info_to_notify = info
        # 锁外回调
        if self._on_status_change:
            try:
                self._on_status_change(info_to_notify)
            except Exception:
                pass

    def _notify(self, info: TaskInfo):
        """调用状态变化回调（线程安全）"""
        if self._on_status_change:
            try:
                self._on_status_change(info)
            except Exception:
                pass
