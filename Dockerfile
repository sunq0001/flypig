FROM python:3.12-slim

WORKDIR /app

# 安装 Node.js 22 LTS
RUN apt-get update -qq \
 && apt-get install -y -qq curl gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y -qq nodejs \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# 复制源码（.dockerignore 已排除无用文件）
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir -e flypig/.[dev]

# 安装前端依赖
RUN cd flypig/interface/web/static_vite && npm ci

# 安装聊天服务依赖
RUN cd flypig/interface/chat-server && npm ci

EXPOSE 8320 8321 5173 8765

CMD ["python", "dev.py"]
