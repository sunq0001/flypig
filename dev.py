"""
FlyPig 开发模式 — 一键启动四个热加载服务 + 崩溃自动重启

启动:  python dev.py
停止:  Ctrl+C 停止全部
特点:  后端/前端/聊天/文档全部热加载，崩溃自动重启（最多 10 次，间隔递增）

重要：输出通过 >> 重定向到 .dev_logs/ 下的独立日志文件，
      避免 Windows asyncio.subprocess.PIPE 因 pipe 关闭而误杀进程。
"""

import asyncio
import sys
from pathlib import Path

# 修复 Windows GBK 编码问题
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

ROOT = Path(__file__).parent
PYTHON = sys.executable

_LOG_DIR = ROOT / ".dev_logs"
_LOG_DIR.mkdir(exist_ok=True)

SERVICES = [
    ("back", "后端 :8320", f"{PYTHON} -m flypig --port 8320 --reload", ROOT),
    (
        "chat",
        "聊天 :8321",
        "node server.js",
        ROOT / "flypig" / "interface" / "chat-server",
    ),
    (
        "front",
        "前端 :5173",
        "node node_modules/vite/bin/vite.js --host --force",
        ROOT / "flypig" / "interface" / "web" / "static_vite",
    ),
    ("docs", "文档 :8765", f"{PYTHON} docs/serve_docs.py --port 8765 --watch", ROOT),
]

_MAX_RETRIES = 10
_POLL_INTERVAL = 5  # 秒，检查进程是否活着


async def run(tag: str, label: str, cmd: str, cwd: Path) -> None:
    retries = 0
    while retries < _MAX_RETRIES:
        # 输出重定向到日志文件，避免 Windows PIPE 问题
        log_file = _LOG_DIR / f"{tag}.log"
        redirected_cmd = f"{cmd} >> {log_file} 2>&1"

        try:
            proc = await asyncio.create_subprocess_shell(
                redirected_cmd,
                cwd=str(cwd),
                # 不捕获 stdout/stderr — 输出已重定向到文件
                stdout=None,
                stderr=None,
            )
        except Exception as e:
            print(f"  [{tag}] 启动失败: {e}")
            retries += 1
            await asyncio.sleep(min(retries * 2, 30))
            continue

        retries = 0
        print(f"  [{tag}] 已启动 ({label}) | 日志: {log_file}")

        # 定期检查进程是否还活着，不用 PIPE 读输出
        while True:
            try:
                await asyncio.sleep(_POLL_INTERVAL)
            except asyncio.CancelledError:
                # Ctrl+C 触发，kill 进程后退出
                try:
                    proc.kill()
                except Exception:
                    pass
                print(f"  [{tag}] 已被停止")
                return

            if proc.returncode is not None:
                # 进程已退出
                break

        code = proc.returncode
        if code == -15 or code == 0 or code is None:
            print(f"  [{tag}] 进程已停止(code={code})")
            return

        delay = min(retries + 1, 5) if retries > 0 else 1
        print(f"  [{tag}] 进程崩溃(code={code})，{delay}秒后重启...")
        retries += 1
        await asyncio.sleep(delay)

    print(f"  [{tag}] 重试 {_MAX_RETRIES} 次仍失败，放弃")


async def main():
    # 检测依赖
    try:
        import flypig  # noqa: F401  # 仅检测包是否可导入
    except ImportError:
        print("错误: flypig 包未安装。请执行:")
        print(f"  pip install -e {ROOT / 'flypig'}")
        sys.exit(1)

    # ── 架构合规检查 ──
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(ROOT / "scripts" / "architecture_check.py"),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        output = stdout.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            print(output)
            print("=" * 60)
            print("  架构检查未通过，请修复后再启动 dev.py")
            print("=" * 60)
            sys.exit(1)
        print(output)
    except FileNotFoundError:
        print("  [check] 架构检查脚本未找到，跳过")
    except TimeoutError:
        print("  [check] 架构检查超时，跳过")

    # ── import-linter 层依赖检查 ──
    try:
        proc = await asyncio.create_subprocess_exec(
            "lint-imports",
            "--config",
            str(ROOT / "flypig" / "pyproject.toml"),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(ROOT),
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            print(output)
            print("=" * 60)
            print("  [lint] 层依赖检查未通过，跳过（不影响开发）")
            print("=" * 60)
        else:
            print(output)
    except FileNotFoundError:
        print("  [lint] import-linter 未安装，跳过（pip install import-linter）")
    except TimeoutError:
        print("  [lint] import-linter 超时，跳过")
    except Exception as exc:
        print(f"  [lint] import-linter 异常: {exc}，跳过")

    print("╔══════════════════════════════════════════╗")
    print("║  FlyPig 开发模式                         ║")
    print("║  Ctrl+C 停止全部 | 崩溃自动重启(最多10次) ║")
    print("╠══════════════════════════════════════════╣")
    for _, label, _, _ in SERVICES:
        print(f"║  {label}")
    print("╚══════════════════════════════════════════╝")
    print()

    tasks = [asyncio.create_task(run(tag, label, cmd, cwd)) for tag, label, cmd, cwd in SERVICES]

    try:
        _ = await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n正在停止全部服务...")
