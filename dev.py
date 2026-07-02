"""
FlyPig 开发模式 — 一键启动四个热加载服务

启动:  python dev.py
停止:  Ctrl+C 停止全部
特点:  后端/前端/聊天/文档全部热加载，崩溃自动重启
"""
import asyncio, sys, os, signal
from pathlib import Path

# 修复 Windows GBK 编码问题
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent
PYTHON = sys.executable  # 用当前 Python

SERVICES = [
    ("back",  "后端 :8320", f"{PYTHON} -m flypig --port 8320",
     ROOT),  # 从项目根目录跑
    ("chat",  "聊天 :8321", f"node server.js",
     ROOT / "flypig" / "interface" / "chat-server"),
    ("front", "前端 :5173", "node node_modules/vite/bin/vite.js --host --force",
     ROOT / "flypig" / "interface" / "web" / "static_vite"),
    ("docs",  "文档 :8765", f"{PYTHON} docs/serve_docs.py --port 8765 --watch",
     ROOT),
]

async def run(tag, label, cmd, cwd):
    while True:
        proc = await asyncio.create_subprocess_shell(
            cmd, cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        print(f"  [{tag}] 已启动 ({label})")
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            text = line.decode('utf-8', errors='replace').rstrip()
            if text:
                print(f"  [{tag}] {text}")
        code = await proc.wait()
        print(f"  [{tag}] 进程退出(code={code})，1秒后自动重启...")
        await asyncio.sleep(1)

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
    print("║  Ctrl+C 停止全部 | 崩溃自动重启          ║")
    print("╠══════════════════════════════════════════╣")
    for _, label, _, _ in SERVICES:
        print(f"║  {label}")
    print("╚══════════════════════════════════════════╝")
    print()

    tasks = [asyncio.create_task(run(tag, label, cmd, cwd))
             for tag, label, cmd, cwd in SERVICES]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n正在停止全部服务...")
