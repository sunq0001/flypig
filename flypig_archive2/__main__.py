"""FlyPig 入口点

用法：
  python -m flypig               # 生产模式
  python -m flypig --dev          # 开发模式（热加载）
"""

import os
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


def main():
    [a for a in sys.argv[1:] if not a.startswith("-")]

    if "--dev" in sys.argv or os.environ.get("FLYPIG_DEV"):
        _run_dev()
    else:
        _run_prod()


def _run_prod():
    """生产模式：直接 serve"""
    import asyncio

    import hypercorn.asyncio
    import hypercorn.config as hc

    from backend.server import create_app
    from domain.config.config import Config

    config = Config()
    app = create_app(config)

    host = "127.0.0.1"
    port = 8321

    print(f"  FlyPig Agent — http://{host}:{port}")

    hc_config = hc.Config()
    hc_config.bind = [f"{host}:{port}"]
    hc_config.loglevel = "warning"
    hc_config.worker_class = "asyncio"

    asyncio.run(hypercorn.asyncio.serve(app, hc_config))


def _run_dev():
    """开发模式：uvicorn + reload — 子进程运行 run_dev.py"""
    import os
    import subprocess
    import sys

    print("  FlyPig Agent (开发模式，热加载) — http://127.0.0.1:8321")

    env = os.environ.copy()
    root_str = str(_root)
    pypath = env.get("PYTHONPATH", "")
    if root_str not in pypath.split(os.pathsep):
        env["PYTHONPATH"] = os.pathsep.join([root_str] + ([pypath] if pypath else []))

    # 子进程运行 run_dev.py（避免 Windows multiprocessing 自举问题）
    proc = subprocess.run(
        [sys.executable, str(_root / "run_dev.py")],
        cwd=str(_root),
        env=env,
    )
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
