"""ASGI 入口 — 供 uvicorn 加载
用法: cd flypig && uvicorn asgi:app --reload

热加载说明：
修改 .py 文件后 uvicorn 自动检测变化并重启子进程。
子进程的 CWD 可能不是 flypig/，所以需要双保险路径。
"""

import os
import sys

# 双保险：用 __file__ 定位 flypig/，再补上 CWD
_root = os.path.dirname(os.path.abspath(__file__))
for p in (_root, os.getcwd()):
    if p and p not in sys.path:
        sys.path.insert(0, p)

from backend.server import create_app
from domain.config.config import Config
from domain.config.model_registry import known_models

print("[asgi] models loaded:", len(known_models()), known_models())

_config = Config()
app = create_app(_config)
