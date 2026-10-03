#!/bin/bash
# FlyPig WSL 开发模式 — 一键启动（崩溃自动重启）
# 依赖: npm install -g concurrently（setup-wsl.sh 已安装）

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

# 修复：WSL 的 /usr/local/bin/node 是 Windows 版，npx 会解析到 Windows 路径
# 必须把 nvm 的 Linux node 放在 PATH 最前面
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
NVM_NODE="$NVM_DIR/versions/node/v22.23.1"
if [ -x "$NVM_NODE/bin/node" ]; then
  export PATH="$NVM_NODE/bin:$PATH"
fi

npx --yes concurrently -k \
  --restart-after=1000 \
  --restart-tries=-1 \
  -n back,chat,front,docs \
  -c cyan,yellow,green,magenta \
  "python3 -m flypig --port 8320 --reload" \
  "cd flypig/interface/chat-server && node server.js" \
  "cd flypig/interface/web/static_vite && node node_modules/vite/bin/vite.js --host --force" \
  "python3 docs/serve_docs.py --port 8765 --watch"
