"""开发模式入口 — uvicorn + reload 热加载
python run_dev.py

改 .py 文件后自动重启，无需手动操作。
"""
import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

import uvicorn

if __name__ == "__main__":
    print(f"  FlyPig Agent (热加载) — http://127.0.0.1:8321")
    print(f"  改 .py 文件后自动重启")

    uvicorn.run(
        "asgi:app",
        host="127.0.0.1",
        port=8321,
        reload=True,
        reload_dirs=[_root],
    )
