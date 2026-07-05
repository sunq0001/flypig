"""沙箱核心模块

提供三层安全隔离：
1. SandboxConfig — 沙箱配置数据类
2. PathValidator — 文件系统路径白名单 + 黑名单 + 运行时审批
3. SandboxManager — Docker 容器管理 + 命令执行双模式
"""

import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

# ──────────────────────────────────────────────
# SandboxConfig
# ──────────────────────────────────────────────


@dataclass
class SandboxConfig:
    """沙箱配置数据类 — 对应 config.yaml 的 sandbox: 段"""

    # 总开关
    enabled: bool = True
    # strict(严格) / mixed(混合) / disable(关闭)
    mode: str = "mixed"

    # Docker 配置
    image: str = "flypig-sandbox:latest"
    container_name: str = "flypig-sandbox"
    cpu_limit: float = 1.0
    memory_limit: str = "1g"
    timeout: int = 120
    network: bool = False

    # 安全加固
    cap_drop_all: bool = True
    no_new_privileges: bool = True
    disk_limit: str = "10g"
    pids_limit: int = 512
    nproc_limit: int = 512
    nofile_limit: int = 256
    read_only_root: bool = True

    # 资源回收
    idle_timeout: int = 300  # 0 = 禁用
    auto_cleanup: bool = True

    # 文件系统
    whitelist_readonly: List[str] = field(default_factory=list)
    whitelist_readwrite: List[str] = field(default_factory=list)
    block_keywords: List[str] = field(
        default_factory=lambda: [
            # Windows 系统路径
            r"C:\Windows\System32",
            r"C:\Windows\System",
            r"C:\Windows\config",
            r"C:\Program Files",
            r"C:\ProgramData",
            # Linux 系统文件
            "/etc/shadow",
            "/etc/passwd",
            "/etc/sudoers",
            "/etc/ssh/",
            "/root",
            "/home",
            # macOS 系统路径
            "/System/",
            "/private/etc/",
        ]
    )

    # 审计日志
    audit_log_path: str = os.path.expanduser("~/.flypig/audit.log")


# ──────────────────────────────────────────────
# PathValidator
# ──────────────────────────────────────────────


class PathValidator:
    """文件系统路径验证 — 白名单 + 黑名单 + 运行时审批"""

    # 硬编码高危关键词（任何模式都不会放行）
    _HARD_BLOCK_KEYWORDS = [
        # Windows
        r"\Windows\System32",
        r"\Windows\System",
        r"\Windows\config",
        # Linux/macOS
        "/etc/shadow",
        "/etc/passwd",
        "/etc/sudoers",
        "/etc/ssh/",
        "/root",
        # 通配
        "..",  # 路径穿越 —— 会在 resolve 后检查
    ]

    def __init__(
        self,
        workspace_dir: str,
        whitelist_readonly: Optional[List[str]] = None,
        whitelist_readwrite: Optional[List[str]] = None,
        block_keywords: Optional[List[str]] = None,
    ):
        self.workspace_dir = Path(workspace_dir).resolve()
        self._readonly: List[Path] = [
            Path(p).resolve() for p in (whitelist_readonly or []) if p
        ]
        self._readwrite: List[Path] = [
            Path(p).resolve() for p in (whitelist_readwrite or []) if p
        ]
        self._block_keywords = block_keywords or []

        # 会话级临时白名单（运行时审批通过后加入）
        self._session_whitelist: List[Path] = []

    # ── 公开 API ──

    def check_path(
        self, path_str: str, mode: str = "read"
    ) -> Tuple[bool, Optional[str]]:
        """验证路径是否允许访问

        Args:
            path_str: 路径字符串
            mode: "read" | "write"

        Returns:
            (allowed: bool, reason: Optional[str])
            allowed=True 表示通过，reason=None
            allowed=False 表示拒绝，reason 为拒绝原因
        """
        try:
            target = Path(path_str).resolve()
        except (OSError, RuntimeError):
            return False, f"Invalid path: {path_str}"

        # ── 1. 黑名单拦截（硬拒绝） ──
        reason = self._check_blocklist(str(target))
        if reason:
            return False, reason

        # ── 2. 工作区检查 ──
        if self._is_subpath(target, self.workspace_dir):
            return True, None

        # ── 3. 配置白名单检查 ──
        for entry in self._readwrite:
            if self._is_subpath(target, entry):
                return True, None

        for entry in self._readonly:
            if self._is_subpath(target, entry):
                return True, None

        # ── 4. 会话白名单检查 ──
        for entry in self._session_whitelist:
            if self._is_subpath(target, entry):
                return True, None

        return False, f"Path outside workspace: {target}"

    def grant_session_access(self, path_str: str):
        """将路径加入会话级临时白名单"""
        p = Path(path_str).resolve()
        if p not in self._session_whitelist:
            self._session_whitelist.append(p)

    def request_path_approval(self, path_str: str, mode: str = "read") -> str:
        """路径被拒绝时弹窗询问用户

        Returns:
            "allow" | "allow_always" | "deny"
        """
        target = Path(path_str).resolve()

        # 双重检查：黑名单路径不弹窗
        reason = self._check_blocklist(str(target))
        if reason:
            return "deny"

        return self._show_approval_dialog(str(target), mode)

    # ── 内部方法 ──

    def _check_blocklist(self, path_str: str) -> Optional[str]:
        """检查是否命中黑名单"""
        path_lower = path_str.lower()

        all_keywords = list(self._HARD_BLOCK_KEYWORDS)
        all_keywords.extend(self._block_keywords)

        for kw in all_keywords:
            if kw.lower() in path_lower:
                return f"Blocked by security policy: path contains '{kw}'"

        return None

    @staticmethod
    def _is_subpath(target: Path, parent: Path) -> bool:
        """检查 target 是否是 parent 的子路径"""
        try:
            target.relative_to(parent)
            return True
        except ValueError:
            return False

    def _show_approval_dialog(self, path: str, mode: str) -> str:
        """弹出系统对话框询问用户

        Returns: "allow" | "allow_always" | "deny"
        """
        mode_label = "只读" if mode == "read" else "读写"
        prompt = (
            f"┌{'─' * 50}┐\n"
            f"│ Flypig: AI 请求访问外部路径{' ' * 21}│\n"
            f"├{'─' * 50}┤\n"
            f"│  路径: {path}\n"
            f"│  模式: {mode_label}\n"
            f"│{' ' * 50}│\n"
            f"│  [y] 允许这次（加入会话白名单）{' ' * 16}│\n"
            f"│  [a] 总是允许（写入 config.yaml）{' ' * 13}│\n"
            f"│  [n] 拒绝（默认）{' ' * 31}│\n"
            f"└{'─' * 50}┘\n"
            f"输入选择 (y/N/a): "
        )

        try:
            if platform.system() == "Windows":
                choice = self._windows_prompt(prompt)
            else:
                choice = self._posix_prompt(prompt)

            choice = choice.strip().lower()
            if choice == "y":
                self.grant_session_access(path)
                return "allow"
            elif choice == "a":
                self.grant_session_access(path)
                return "allow_always"
            else:
                return "deny"
        except Exception:
            return "deny"

    @staticmethod
    def _windows_prompt(prompt: str) -> str:
        """Windows 下用 PowerShell 弹提示框"""
        # 用 PS 的 Read-Host，超时 30 秒
        escaped = prompt.replace("'", "''")
        ps_cmd = (
            f'$host.UI.RawUI.WindowTitle = "Flypig - 路径审批"; '
            f"Write-Host '{escaped}'; "
            f"$resp = Read-Host; "
            f"Write-Output $resp"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            return result.stdout.strip() or "n"
        except subprocess.TimeoutExpired:
            return "n"
        except Exception:
            return "n"

    @staticmethod
    def _posix_prompt(prompt: str) -> str:
        """POSIX 下用 input 提示"""
        print(prompt, end="", flush=True)
        try:
            import select

            ready, _, _ = select.select([sys.stdin], [], [], 30)
            if ready:
                return sys.stdin.readline()
            return "n"
        except Exception:
            return "n"


# ──────────────────────────────────────────────
# SandboxManager
# ──────────────────────────────────────────────


class SandboxManager:
    """Docker 沙箱管理器 — 容器生命周期 + 命令执行 + 安全防护"""

    # 高危命令模式 —— 命中后需要用户确认
    DANGEROUS_PATTERNS = [
        re.compile(r"\brm\s+-rf\s+[/~]"),
        re.compile(r"\brm\s+-rf\s+/\*"),
        re.compile(r"\bdd\s+if="),
        re.compile(r"\bmkfs\b"),
        re.compile(r"\bfdisk\b"),
        re.compile(r"\bparted\b"),
        re.compile(r"\bformat\b"),
        re.compile(r"\bchmod\s+777\s+/"),
        re.compile(r"\bchown\s+-R\s+/"),
        re.compile(r">\s+/dev/sd"),
        re.compile(r">\s+/dev/nvme"),
        re.compile(r"\bwget\b.*\|\s*(bash|sh)"),
        re.compile(r"\bcurl\b.*\|\s*(bash|sh)"),
        re.compile(r"docker\s+run\s+--privileged"),
    ]

    # 逃逸模式 —— 直接拒绝，不弹窗
    ESCAPE_PATTERNS = [
        re.compile(r"docker\s+run\s+--privileged"),
        re.compile(r"docker\s+run\s+--pid=host"),
        re.compile(r"docker\s+run\s+--net=host"),
        re.compile(r"docker\s+exec\s+--privileged"),
        re.compile(r"nsenter\b"),
        re.compile(r"mount\s+-o\s+bind\s+/"),
    ]

    def __init__(self, config: SandboxConfig, workspace_dir: str):
        self.config = config
        self.workspace_dir = Path(workspace_dir).resolve()
        self._container_name = config.container_name
        self._image_name = config.image
        self._container_id: Optional[str] = None
        self._last_activity = time.time()
        self._idle_monitor: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()
        self._lock = threading.Lock()

        # 审计日志路径
        self._audit_path = Path(config.audit_log_path)
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)

        # 在沙箱模式下，白名单只读路径需要挂入容器
        self._extra_volumes: List[Tuple[str, str, str]] = []
        for p in config.whitelist_readonly:
            resolved = Path(p).resolve()
            if resolved.exists():
                # 挂载到容器内的 /host-<name>
                mount_point = f"/host-{resolved.name}"
                self._extra_volumes.append((str(resolved), mount_point, "ro"))

    # ── 容器生命周期 ──

    def ensure_container(self):
        """确保容器已创建并运行"""
        if self._is_container_running():
            return

        with self._lock:
            if self._is_container_running():
                return

            # 先清理同名旧容器
            self._remove_existing()

            # 1. 检查镜像
            if not self._image_exists():
                self._build_image()

            # 2. 创建容器
            self._create_container()

            # 3. 启动
            self._start_container()

            # 4. 启动后校验
            self._verify_mounts()

            # 5. 启动闲置监控
            self._start_idle_monitor()

    def cleanup(self):
        """退出清理 —— 销毁容器"""
        self._stop_idle_monitor()
        if self.config.auto_cleanup:
            try:
                subprocess.run(
                    ["docker", "rm", "-f", self._container_name],
                    capture_output=True,
                    timeout=10,
                )
            except Exception:
                pass

    # ── 命令执行 ──

    def _validate_workdir(self, workdir: str) -> Optional[str]:
        """校验容器内 workdir 是否存在，不存在时返回诊断信息"""
        try:
            check = subprocess.run(
                [
                    "docker",
                    "exec",
                    self._container_name,
                    "bash",
                    "-c",
                    f"test -d {shlex.quote(workdir)} && echo OK || echo MISSING",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
            if "MISSING" in check.stdout:
                listing = self._list_container_dir("/workspace")
                return (
                    f"[PATH ERROR] Directory not found: {workdir}\n"
                    f"[HINT] Your workspace folder '{self.workspace_dir.name}' is "
                    f"mounted at /workspace inside the container.\n"
                    f"       To access subdirectories, use: cd /workspace/<subfolder_name>\n"
                    f"       Available directories in /workspace:{listing}\n"
                    f"[FIX] Check the exact subdirectory name and correct the path."
                )
        except Exception:
            pass  # 校验失败不阻塞，让后面的实际执行去报错
        return None

    def _list_container_dir(self, path: str = "/workspace") -> str:
        """列出容器内指定路径的非隐藏目录"""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    self._container_name,
                    "bash",
                    "-c",
                    f"ls -1d {shlex.quote(path)}/*/ 2>/dev/null || echo '(empty)'",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
            items = [l.strip() for l in result.stdout.split("\n") if l.strip()]
            if not items or items == ["(empty)"]:
                return "\n       (no subdirectories)"
            shown = items[:15]
            text = "\n" + "\n".join(f"       - {d}" for d in shown)
            if len(items) > 15:
                text += f"\n       ... and {len(items) - 15} more"
            return text
        except Exception:
            return (
                "\n       (unable to list, may need a moment after container creation)"
            )

    def run_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        workdir: Optional[str] = None,
    ) -> str:
        """阻塞模式：在容器内执行命令并返回 stdout/stderr

        适合一次性命令（git/pip/compile）
        """
        # 高危检测
        if self._is_escape_command(command):
            return "[SECURITY] Container escape attempt blocked."

        if self._is_dangerous_command(command):
            approved = self._request_user_approval(command)
            if not approved:
                return "[SECURITY] Command rejected by user."

        self.ensure_container()

        timeout = timeout or self.config.timeout
        workdir = workdir or "/workspace"

        # ── 前置校验：检查 workdir 在容器内是否存在 ──
        dir_check = self._validate_workdir(workdir)
        if dir_check is not None:
            return dir_check

        full_cmd = ["docker", "exec"]
        if timeout:
            full_cmd.extend(["-e", f"TIMEOUT={timeout}"])

        full_cmd.extend(
            [
                self._container_name,
                "timeout",
                str(timeout),
                "bash",
                "-c",
                f"cd {shlex.quote(workdir)} && {command}",
            ]
        )

        start_time = time.time()
        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout + 10,
            )
            elapsed = time.time() - start_time
            self._update_activity()

            output = result.stdout or ""
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"

            # ── 命令失败时附加诊断 ──
            if result.returncode != 0:
                error_lower = (result.stderr or "").lower()
                stderr_text = result.stderr or ""

                # 检测交互式脚本（input() 无 stdin 导致的 EOFError）
                if "eof" in error_lower or "eof when reading" in error_lower:
                    output += (
                        "\n\n[INTERACTIVE] This script needs user input (input() without stdin).\n"
                        "[HINT] Retry with persist=True to run in the interactive terminal.\n"
                    )

                if (
                    "no such file or directory" in error_lower
                    or "not found" in error_lower
                ):
                    listing = self._list_container_dir("/workspace")
                    output += (
                        f"\n[PATH ERROR] The directory may not exist.\n"
                        f"[HINT] Your workspace folder is mounted at /workspace.\n"
                        f"       The workspace folder name is: {self.workspace_dir.name}\n"
                        f"       Available subdirectories in /workspace:{listing}\n"
                        f"[FIX] Use the exact path: cd /workspace/<subfolder>"
                    )
                output += f"\n[exit code: {result.returncode}]"

            # 审计
            self._audit_log(command, result.returncode, elapsed)

            return output.strip()
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            self._audit_log(command, -1, elapsed)
            return f"[TIMEOUT] Command did not complete within {timeout}s"
        except Exception as e:
            return f"[ERROR] {e}"

    def spawn_command(self, command: str, workdir: Optional[str] = None) -> str:
        """非阻塞模式：在新终端窗口运行 docker exec -it

        适合长驻命令（npm run dev / python server.py / tail -f）
        """
        self.ensure_container()
        docker_cmd = (
            f"docker exec -it {self._container_name} "
            f"bash -c 'cd {shlex.quote(workdir)} && {command}'"
        )

        system = platform.system()

        try:
            if system == "Windows":
                if os.environ.get("TERM_PROGRAM") == "vscode":
                    # VS Code 终端标签页
                    return self._spawn_vscode_terminal(docker_cmd)
                else:
                    # PowerShell / cmd 新窗口
                    return self._spawn_windows_terminal(docker_cmd)
            else:
                # Linux / macOS
                return self._spawn_posix_terminal(docker_cmd)
        except Exception as e:
            return f"[ERROR] Failed to spawn terminal: {e}"

    # ── 镜像管理 ──

    def _image_exists(self) -> bool:
        """检查 Docker 镜像是否存在"""
        try:
            result = subprocess.run(
                ["docker", "images", "-q", self._image_name],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    def _build_image(self):
        """构建沙箱 Docker 镜像"""
        dockerfile = Path(__file__).parent / "Dockerfile.sandbox"
        if not dockerfile.exists():
            print("[Sandbox] Dockerfile.sandbox not found, creating default...")
            self._create_default_dockerfile(dockerfile)

        print(f"[Sandbox] Building image {self._image_name}...")
        try:
            subprocess.run(
                ["docker", "build", "-t", self._image_name, "-f", str(dockerfile), "."],
                cwd=Path(__file__).parent,
                check=True,
                timeout=120,
            )
            print(f"[Sandbox] Image {self._image_name} built successfully.")
        except subprocess.TimeoutExpired:
            print("[Sandbox] Image build timed out. Building in background...")
            subprocess.Popen(
                ["docker", "build", "-t", self._image_name, "-f", str(dockerfile), "."],
                cwd=Path(__file__).parent,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            print(f"[Sandbox] Image build failed: {e}")
            raise

    @staticmethod
    def _create_default_dockerfile(path: Path):
        """创建默认的 Dockerfile.sandbox"""
        content = r"""FROM python:3.11-alpine

RUN apk add --no-cache \
        bash \
        git \
        nodejs \
        npm \
        gcc \
        g++ \
        musl-dev \
        sudo

# 创建非 root 用户 + passwordless sudo
RUN adduser -D -h /home/flypig flypig && \
    echo "flypig ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER flypig
WORKDIR /workspace

CMD ["tail", "-f", "/dev/null"]
"""
        path.write_text(content)

    # ── 容器操作 ──

    def _is_container_running(self) -> bool:
        """检查容器是否在运行"""
        try:
            result = subprocess.run(
                ["docker", "ps", "-q", "-f", f"name={self._container_name}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
            if result.stdout.strip():
                self._container_id = result.stdout.strip()[:12]
                return True
            return False
        except Exception:
            return False

    def _remove_existing(self):
        """移除同名旧容器"""
        try:
            subprocess.run(
                ["docker", "rm", "-f", self._container_name],
                capture_output=True,
                timeout=10,
            )
        except Exception:
            pass

    def _create_container(self):
        """创建容器（参数硬编码，防止拼接注入）"""
        cmd = [
            "docker",
            "create",
            "--name",
            self._container_name,
            "-v",
            f"{self.workspace_dir}:/workspace:rw",
            "-w",
            "/workspace",
            "--user",
            "flypig",
        ]

        # ── 安全加固参数（硬编码） ──
        if self.config.cap_drop_all:
            cmd.append("--cap-drop=ALL")
        if self.config.no_new_privileges:
            cmd.append("--security-opt=no-new-privileges:true")
        if self.config.disk_limit:
            cmd.extend(["--storage-opt", f"size={self.config.disk_limit}"])
        if self.config.pids_limit:
            cmd.extend(["--pids-limit", str(self.config.pids_limit)])

        cmd.extend(
            [
                "--ulimit",
                f"nproc={self.config.nproc_limit}",
                "--ulimit",
                f"nofile={self.config.nofile_limit}",
            ]
        )

        if self.config.read_only_root:
            cmd.extend(
                [
                    "--read-only",
                    "--tmpfs",
                    "/tmp:size=100m,noexec,nosuid",
                    "--tmpfs",
                    "/home/flypig/.cache:size=50m",
                ]
            )

        if self.config.network:
            cmd.extend(["--network", "bridge"])
        else:
            cmd.extend(["--network", "none"])

        if self.config.memory_limit:
            cmd.extend(["--memory", self.config.memory_limit])
        if self.config.cpu_limit:
            cmd.extend(["--cpus", str(self.config.cpu_limit)])

        # ── 额外只读卷挂载（白名单路径） ──
        for host_path, mount_point, perm in self._extra_volumes:
            cmd.extend(["-v", f"{host_path}:{mount_point}:{perm}"])

        cmd.append(f"{self._image_name}")
        cmd.extend(["tail", "-f", "/dev/null"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to create container: {result.stderr}")
            self._container_id = result.stdout.strip()[:12]
        except subprocess.TimeoutExpired:
            raise RuntimeError("Docker create timed out")

    def _start_container(self):
        """启动容器"""
        try:
            subprocess.run(
                ["docker", "start", self._container_name],
                check=True,
                capture_output=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Docker start timed out")

    def _verify_mounts(self):
        """启动后校验挂载列表"""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    self._container_name,
                    "--format",
                    "{{json .Mounts}}",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            if result.returncode != 0:
                self._panic("Container verification failed: inspect error")

            mounts = json.loads(result.stdout)
            if len(mounts) < 1:
                self._panic("Container has no mounts")

            # 检查主挂载点是否为工作区
            primary_mount = mounts[0]
            if primary_mount.get("Destination") != "/workspace":
                self._panic(f"Unexpected primary mount: {primary_mount}")

            # 检查是否只有工作区 + 额外挂载（白名单）
            expected_count = 1 + len(self._extra_volumes)
            if len(mounts) != expected_count:
                self._panic(
                    f"Unexpected mount count: {len(mounts)} (expected {expected_count})"
                )

            # 检查 Privileged 标志
            priv_result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    self._container_name,
                    "--format",
                    "{{.HostConfig.Privileged}}",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
            if priv_result.stdout.strip() != "false":
                self._panic("Container has privileged access!")

        except json.JSONDecodeError:
            self._panic("Mount verification failed: invalid JSON")

    def _panic(self, reason: str):
        """致命错误 —— 销毁容器并抛出"""
        print(f"[SANDBOX CRITICAL] {reason}")
        try:
            subprocess.run(
                ["docker", "rm", "-f", self._container_name],
                capture_output=True,
                timeout=10,
            )
        except Exception:
            pass
        raise RuntimeError(f"Sandbox security violation: {reason}")

    # ── 高危命令检测 ──

    def _is_dangerous_command(self, command: str) -> bool:
        """检测是否高危命令（需要用户确认）"""
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.search(command):
                return True
        return False

    def _is_escape_command(self, command: str) -> bool:
        """检测是否逃逸命令（直接拒绝）"""
        for pattern in self.ESCAPE_PATTERNS:
            if pattern.search(command):
                return True
        return False

    def _request_user_approval(self, command: str) -> bool:
        """高危命令 —— 弹窗要求用户确认"""
        prompt = (
            f"┌{'─' * 50}┐\n"
            f"│ Flypig: 高危命令确认{' ' * 29}│\n"
            f"├{'─' * 50}┤\n"
            f"│  命令: {command[:80]}\n"
            f"│{' ' * 50}│\n"
            f"│  沙箱内可执行，但可能误删工作区文件。{' ' * 5}│\n"
            f"│{' ' * 50}│\n"
            f"│  确认执行？(y/N) {' ' * 29}│\n"
            f"└{'─' * 50}┘\n"
            f"输入 y 确认: "
        )

        try:
            if platform.system() == "Windows":
                escaped_prompt = prompt.replace("'", "''")
                ps_cmd = (
                    '$host.UI.RawUI.WindowTitle = "Flypig - \u9ad8\u5371\u547d\u4ee4\u786e\u8ba4"; '
                    f"Write-Host '{escaped_prompt}'; "
                    "$resp = Read-Host; "
                    "if ($resp -eq 'y') { Write-Output 'yes' } else { Write-Output 'no' }"
                )
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                )
                return result.stdout.strip() == "yes"
            else:
                print(prompt, end="", flush=True)
                import select

                ready, _, _ = select.select([sys.stdin], [], [], 30)
                if ready:
                    return sys.stdin.readline().strip().lower() == "y"
                return False
        except Exception:
            return False

    # ── 闲置回收 ──

    def _update_activity(self):
        """更新最后一次活动时间"""
        self._last_activity = time.time()

    def _start_idle_monitor(self):
        """启动闲置回收线程"""
        if self.config.idle_timeout <= 0:
            return

        if self._idle_monitor is not None and self._idle_monitor.is_alive():
            return

        self._stop_monitor.clear()
        self._idle_monitor = threading.Thread(
            target=self._idle_monitor_loop,
            daemon=True,
        )
        self._idle_monitor.start()

    def _idle_monitor_loop(self):
        """闲置回收循环"""
        while not self._stop_monitor.is_set():
            idle = time.time() - self._last_activity
            if idle > self.config.idle_timeout:
                try:
                    subprocess.run(
                        ["docker", "stop", self._container_name],
                        capture_output=True,
                        timeout=15,
                    )
                except Exception:
                    pass
                # 等待唤醒
                while not self._stop_monitor.is_set():
                    if self._is_container_running():
                        break
                    time.sleep(5)
            time.sleep(30)

    def _stop_idle_monitor(self):
        """停止闲置回收线程"""
        self._stop_monitor.set()

    # ── 审计日志 ──

    def _audit_log(self, command: str, exit_code: int, elapsed: float):
        """记录审计日志"""
        ts = datetime.now(timezone.utc).isoformat()
        cmd_hash = hashlib.sha256(command.encode()).hexdigest()[:16]
        entry = {
            "ts": ts,
            "cmd": command,
            "cmd_hash": cmd_hash,
            "exit_code": exit_code,
            "elapsed_s": round(elapsed, 2),
        }
        try:
            with open(self._audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass  # 审计日志写入失败不阻塞执行

    # ── 终端弹出 ──

    def _spawn_vscode_terminal(self, cmd: str) -> str:
        """VS Code 终端标签页"""
        script_dir = Path("/tmp/flypig")
        script_dir.mkdir(parents=True, exist_ok=True)
        script_path = script_dir / f"cmd_{int(time.time())}.sh"
        script_path.write_text(f"#!/bin/bash\n{cmd}\necho ''\nexec bash\n")
        script_path.chmod(0o755)

        subprocess.Popen(
            ["code", "--command", "workbench.action.terminal.new"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return (
            f"[VS Code 新终端已打开 (沙箱容器)]\n"
            f"   命令: {cmd}\n"
            f"   在新终端中执行: source {script_path}"
        )

    def _spawn_windows_terminal(self, cmd: str) -> str:
        """Windows 新窗口"""
        if os.environ.get("PSModulePath"):
            shell_name = "powershell"
            # 在 PS 中启动 cmd.exe 开新窗口跑 docker exec
            start_cmd = (
                f'start "FlyPig (Sandbox)" cmd /k '
                f'"{cmd} & echo. & echo [Press Ctrl+C to exit] & pause >nul"'
            )
        else:
            shell_name = "cmd"
            start_cmd = f'start "FlyPig (Sandbox)" cmd /k "{cmd} & echo. & pause"'

        subprocess.Popen(start_cmd, shell=True)
        self._update_activity()
        return f"[Started in new {shell_name} window (sandbox)]\n   {cmd}"

    def _spawn_posix_terminal(self, cmd: str) -> str:
        """POSIX 新终端窗口"""
        workspace = str(self.workspace_dir)

        terminals = [
            (
                "gnome-terminal",
                [
                    "gnome-terminal",
                    "--",
                    "bash",
                    "-c",
                    f"cd '{workspace}' && {cmd}; echo; read -p '按 Enter 关闭...'",
                ],
            ),
            ("xterm", ["xterm", "-hold", "-e", f"cd '{workspace}' && {cmd}"]),
            ("konsole", ["konsole", "--hold", "-e", f"cd '{workspace}' && {cmd}"]),
        ]

        for term_name, term_cmd in terminals:
            try:
                subprocess.run(["which", term_name], capture_output=True, timeout=2)
                subprocess.Popen(
                    term_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                self._update_activity()
                return f"[Started in {term_name} (sandbox)]\n   {cmd}"
            except Exception:
                continue

        # fallback: nohup
        log_path = f"/tmp/flypig_sandbox_{int(time.time())}.log"
        bg_cmd = f"nohup bash -c 'cd {workspace} && {cmd}' > {log_path} 2>&1 &"
        subprocess.Popen(bg_cmd, shell=True)
        return f"[Running in background (sandbox)]\n   {cmd}\n[Log] tail -f {log_path}"


# ──────────────────────────────────────────────
# 便利函数：检测 Docker Desktop 是否可用
# ──────────────────────────────────────────────


def is_docker_available() -> bool:
    """检测 Docker Desktop/Daemon 是否可用"""
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def create_sandbox_components(
    config: SandboxConfig,
    workspace_dir: str,
) -> Tuple[Optional[SandboxManager], Optional[PathValidator]]:
    """创建沙箱组件

    自动检测 Docker 可用性，不可用则返回 None + 打印警告
    """
    if config.mode == "disable":
        return None, None

    # 文件系统验证器始终创建（即使 Docker 不可用）
    validator = PathValidator(
        workspace_dir=workspace_dir,
        whitelist_readonly=config.whitelist_readonly,
        whitelist_readwrite=config.whitelist_readwrite,
        block_keywords=config.block_keywords,
    )

    if not config.enabled:
        return None, validator

    if not is_docker_available():
        print(
            "[Sandbox] Warning: Docker Desktop not running, sandbox command execution disabled"
        )
        print("[Sandbox]   File system access still protected by PathValidator")
        return None, validator

    manager = SandboxManager(config, workspace_dir)
    return manager, validator
