FROM nikolaik/python-nodejs:python3.11-nodejs20

WORKDIR /app

# 复制源码
COPY . .

# 安装 Python 依赖
RUN pip install -e flypig/.[dev]

# 安装前端依赖
RUN cd flypig/interface/web/static_vite && npm ci

EXPOSE 8320 8321 5173 8765

CMD ["python", "dev.py"]
