# 运维部署

> **来源**: `architecture-refactor.md` §6
> **关联文档**: `migration-roadmap.md`（迁移步骤）、`tech-stack.md`（技术选型）

---

## 一、阶段式演进

```text
单机版：docker-compose (api + db + nginx)
              ↓
SaaS：  docker-compose (api + db + nginx + redis)
```

---

## 二、Docker Compose

### docker-compose.yml

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports: ["8321:8321"]
    volumes:
      - ".:/app"
      - "./data:/app/data"           # 持久化：对话数据 + checkpoints
      - "/app/__pycache__"
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - QWEN_API_KEY=${QWEN_API_KEY}
      - FLYPIG_WORKSPACE=/app/workspace
      - FLYPIG_DB_PATH=/app/data/conversations.db
      - LANGGRAPH_DB_PATH=/app/data/langgraph.db
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - "./nginx.conf:/etc/nginx/nginx.conf:ro"
      - "./web/static:/usr/share/nginx/html:ro"
    profiles: ["prod"]
```

### 使用方式

```bash
# 启动
docker compose up -d

# 查看日志
docker compose logs -f api

# 更新
docker compose pull && docker compose up -d
```

### 数据持久化

| 目录 | 内容 | 备份策略 |
|------|------|---------|
| `./data/conversations.db` | IConversationStore（对话记录） | 每日定时备份 |
| `./data/langgraph.db` | LangGraph Checkpointer（会话状态） | 随 conversations.db 一起 |
| `./workspace/` | 用户工作区代码 | 由用户自行版本管理 |

---

## 三、CI/CD 流水线

### 阶段 1（MVP — GitHub Actions）

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install ruff
      - run: ruff check flypig/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
      - run: pytest tests/
```

### 阶段 2（SaaS — 自动部署）

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t flypig-api .
      - run: docker tag flypig-api ghcr.io/${{ github.repository }}:latest
      - run: docker push ghcr.io/${{ github.repository }}:latest
      - run: |
          ssh deploy@${{ secrets.HOST }} "
            docker pull ghcr.io/${{ github.repository }}:latest
            docker compose --profile prod up -d
          "
```

---

## 四、环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API Key |
| `QWEN_API_KEY` | ✅ | 通义千问 API Key（备用） |
| `FLYPIG_WORKSPACE` | ❌ | 工作区路径（默认 /app/workspace） |
| `FLYPIG_DB_PATH` | ❌ | 数据库路径 |
| `LANGGRAPH_DB_PATH` | ❌ | LangGraph Checkpointer 路径 |
| `LOG_LEVEL` | ❌ | 日志级别（默认 INFO） |

---

## 五、健康检查

```python
@app.route("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "db": "connected" if check_db() else "error",
        "uptime": time.time() - start_time,
    }

@app.route("/ready")
async def ready():
    """就绪检查（Kubernetes 探针用）"""
    return {"status": "ready"}
```

---

## 六、SaaS 阶段扩展

| 组件 | 用途 | 引入时机 |
|------|------|---------|
| **PostgreSQL** | 替代 SQLite，支持并发读写 + pgvector 向量搜索 | 多用户并发 > 10 |
| **Redis** | 会话缓存 + SSE 发布订阅（多实例时需要） | 多实例部署 |
| **Prometheus + Grafana** | 监控 LLM token 消耗、API 延迟、错误率 | SaaS 上线前 |
| **Sentry** | 错误追踪 | SaaS 上线前 |
| **CDN** | 前端静态文件加速 | SaaS 上线前 |

---

> **当前阶段（单机版）**：docker-compose (api + db + nginx) 一键部署。CI/CD 只需 lint + test。
