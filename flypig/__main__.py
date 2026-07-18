"""FlyPig 入口点

为什么做：作为 python -m flypig 的入口，启动 HTTP 服务。
实现方法：
  --reload 模式 → uvicorn.run()（热加载可靠，Windows 友好）
  默认模式    → Hypercorn serve()（生产级 ASGI 服务器）

层&依赖：bootstrap 层，依赖 bootstrap.app_factory + uvicorn (dev) / hypercorn (prod)
"""

from __future__ import annotations

import argparse

from flypig.bootstrap import create_app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8320)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--reload", action="store_true", help="启用热重载（开发模式）")
    args = parser.parse_args()

    msg = f"  FlyPig Agent — http://{args.host}:{args.port}"

    if args.reload:
        # ── 开发模式：uvicorn.run() ──
        # uvicorn.run() 传入模块路径字符串 "module:app_factory()"，
        # 内部 reloader 检测到文件变化后重新 import，保证拿到新代码。
        # 不再传 app 对象，避免 reloader 持有旧对象引用。
        import uvicorn

        msg += " (v2 热重载)"
        print(msg)
        uvicorn.run(
            "flypig.bootstrap:create_app",
            host=args.host,
            port=args.port,
            reload=True,
            reload_dirs=["flypig"],  # 只监控 flypig/ 目录，根目录的临时文件不触发 reload
            factory=True,
            log_level="warning",
        )
    else:
        # ── 生产模式：Hypercorn serve() ──
        # 直接传 app 对象，无 reloader 开销
        import asyncio

        from hypercorn.asyncio import serve
        from hypercorn.config import Config as HCConfig

        app = create_app()
        cfg = HCConfig()
        cfg.bind = [f"{args.host}:{args.port}"]
        cfg.loglevel = "warning"
        cfg.worker_class = "asyncio"
        print(msg)
        asyncio.run(serve(app, cfg))


if __name__ == "__main__":
    main()
