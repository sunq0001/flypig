#!/bin/bash
# FlyPig WSL 开发模式 — 一键启动（崩溃自动重启）

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "╔══════════════════════════════════════════╗"
echo "║  FlyPig WSL 开发模式                     ║"
echo "║  Ctrl+C 停止全部 | 自动重启崩溃的服务    ║"
echo "╠══════════════════════════════════════════╣"
echo "║  后端:8320  前端:5173  聊天:8321  文档:8765║"
echo "╚══════════════════════════════════════════╝"

cd "$ROOT"

# PYTHONPATH 指向项目根，python3 -m flypig 就能找到自己的模块
export PYTHONPATH="$ROOT:$PYTHONPATH"

npx concurrently -k \
  --restart-after=1000 \
  --restart-tries=-1 \
  -n back,chat,front,docs \
  -c cyan,yellow,green,magenta \
  "python3 -m flypig --port 8320" \
  "cd flypig/interface/chat-server && node server.js" \
  "cd flypig/interface/web/static_vite && npx vite --host" \
  "python3 docs/serve_docs.py --port 8765 --watch"
