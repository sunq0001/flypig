"""
FlyPig 开发模式 — 一键启动三个热加载服务（单窗口）

启动:  python dev.py
停止:  Ctrl+C 停止全部
"""
import asyncio, sys, os
from pathlib import Path

# 修复 Windows GBK 编码问题
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent

SERVICES = [
    ("back",  "后端Quart  :8320", f"cd /d {ROOT / 'flypig'} && python -m uvicorn asgi:app --reload --host 127.0.0.1 --port 8320"),
    ("chat",  "对话(Node) :8321", f"cd /d {ROOT / 'flypig' / 'backend' / 'chat-server'} && node server.js"),
    ("front", "前端       :5173", f"cd /d {ROOT / 'flypig' / 'frontend' / 'static_vite'} && npx vite --host"),
    ("docs",  "文档       :8765", f"python {ROOT / 'docs' / 'serve_docs.py'} --port 8765 --watch"),
]

async def run(tag, label, cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        text = line.decode('utf-8', errors='replace').rstrip()
        if text:
            print(f"[{tag}] {text}")
    await proc.wait()

async def main():
    print("╔══════════════════════════════════════════╗")
    print("║  FlyPig 开发模式 — 按 Ctrl+C 停止全部    ║")
    print("╠══════════════════════════════════════════╣")
    for _, label, _ in SERVICES:
        print(f"║  {label}")
    print("╚══════════════════════════════════════════╝")
    print()

    tasks = [asyncio.create_task(run(tag, label, cmd)) for tag, label, cmd in SERVICES]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n正在停止全部服务...")
