"""
FlyPig 开发模式 — 一键启动四个热加载服务 + 崩溃自动重启

启动:  python dev.py
停止:  Ctrl+C 停止全部
特点:  后端/前端/聊天/文档全部热加载，崩溃自动重启（最多 10 次，间隔递增）
"""
import asyncio, sys, os, signal, time
from pathlib import Path

# 修复 Windows GBK 编码问题
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent
PYTHON = sys.executable

SERVICES = [
    ("back",  "后端 :8320", f"{PYTHON} -m flypig --port 8320",
     ROOT),
    ("chat",  "聊天 :8321", f"node server.js",
     ROOT / "flypig" / "interface" / "chat-server"),
    ("front", "前端 :5173", "node node_modules/vite/bin/vite.js --host --force",
     ROOT / "flypig" / "interface" / "web" / "static_vite"),
    ("docs",  "文档 :8765", f"{PYTHON} docs/serve_docs.py --port 8765 --watch",
     ROOT),
]

_MAX_RETRIES = 10


async def run(tag, label, cmd, cwd):
    retries = 0
    while retries < _MAX_RETRIES:
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd, cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except Exception as e:
            print(f"  [{tag}] 启动失败: {e}")
            retries += 1
            await asyncio.sleep(min(retries * 2, 30))
            continue

        retries = 0  # 启动成功重置计数
        print(f"  [{tag}] 已启动 ({label})")

        # 带超时读 stdout，防止僵死进程 hang 住 readline
        while True:
            try:
                line = await asyncio.wait_for(
                    proc.stdout.readline(), timeout=5
                )
                if not line:
                    break
                text = line.decode('utf-8', errors='replace').rstrip()
                if text:
                    print(f"  [{tag}] {text}")
            except asyncio.TimeoutError:
                # 5 秒无输出不代表进程已死，检查进程是否还活着
                if proc.returncode is not None:
                    break
                continue

        # 进程已死，等它完全退出
        try:
            code = await asyncio.wait_for(proc.wait(), timeout=3)
        except asyncio.TimeoutError:
            print(f"  [{tag}] 进程无响应，强制终止")
            try:
                proc.kill()
            except Exception:
                pass
            code = -1

        if code == -15 or code == 0:
            # -15 = SIGTERM（正常停止）, 0 = 正常退出
            print(f"  [{tag}] 进程已停止(code={code})")
            return
        else:
            delay = min(retries + 1, 5) if retries > 0 else 1
            print(f"  [{tag}] 进程崩溃(code={code})，{delay}秒后重启...")
            retries += 1
            await asyncio.sleep(delay)

    print(f"  [{tag}] 重试 {_MAX_RETRIES} 次仍失败，放弃")


async def main():
    # 检测依赖
    try:
        import flypig
    except ImportError:
        print("错误: flypig 包未安装。请执行:")
        print(f"  pip install -e {ROOT / 'flypig'}")
        sys.exit(1)

    print("╔══════════════════════════════════════════╗")
    print("║  FlyPig 开发模式                         ║")
    print("║  Ctrl+C 停止全部 | 崩溃自动重启(最多10次) ║")
    print("╠══════════════════════════════════════════╣")
    for _, label, _, _ in SERVICES:
        print(f"║  {label}")
    print("╚══════════════════════════════════════════╝")
    print()

    tasks = [asyncio.create_task(run(tag, label, cmd, cwd))
             for tag, label, cmd, cwd in SERVICES]

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n正在停止全部服务...")
