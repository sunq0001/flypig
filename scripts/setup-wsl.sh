#!/bin/bash
# FlyPig WSL 开发环境一键配置
# 用 WSL2 Ubuntu 跑: bash scripts/setup-wsl.sh

set -e

echo "=== FlyPig WSL 环境配置 ==="

# 1. 修复 localhost 代理警告
echo ">>> 配置 WSL 代理..."
cat > /etc/wsl.conf 2>/dev/null << 'EOF'
[network]
hostname = flypig-dev
generateResolvConf = true
EOF

# 2. 安装 Node.js (via nvm, 轻量)
if ! command -v node &>/dev/null; then
  echo ">>> 安装 nvm + Node.js..."
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
  nvm install 22
  nvm use 22
else
  echo ">>> Node.js 已安装: $(node -v)"
fi

# 3. 安装 concurrently
npm install -g concurrently 2>/dev/null || true

# 4. 安装项目前端依赖
echo ">>> 安装前端依赖..."
cd /mnt/c/Users/mss/WorkBuddy/Flypig-agent/flypig/interface/web/static_vite
npm install

# 5. 安装聊天服务依赖
echo ">>> 安装聊天服务依赖..."
cd /mnt/c/Users/mss/WorkBuddy/Flypig-agent/flypig/interface/chat-server
npm install

# 6. 安装 Python 包
echo ">>> 安装 Python 包..."
cd /mnt/c/Users/mss/WorkBuddy/Flypig-agent/flypig
pip3 install -e .

echo ""
echo "=== 配置完成! ==="
echo "运行: bash scripts/dev-wsl.sh"
