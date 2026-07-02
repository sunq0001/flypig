"""FlyPig 入口点"""
import asyncio
import argparse
from hypercorn.asyncio import serve
from hypercorn.config import Config as HCConfig
from flypig.bootstrap import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8320)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    app = create_app()
    cfg = HCConfig()
    cfg.bind = [f"{args.host}:{args.port}"]
    cfg.loglevel = "warning"
    cfg.worker_class = "asyncio"
    print(f"  FlyPig Agent — http://{args.host}:{args.port}")
    asyncio.run(serve(app, cfg))


if __name__ == "__main__":
    main()
