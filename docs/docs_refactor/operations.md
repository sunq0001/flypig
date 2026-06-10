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

## 二、Docker 镜像

### Dockerfile

```dockerfile
# ── 第一阶段：构建前端 ──
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY web/static_vite/package.json web/static_vite/ .
RUN npm install && npm run build
# 产物在 /app/dist/

# ── 第二阶段：Python 后端 ──
FROM python:3.12-slim
WORKDIR /app

# 后端依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[prod]"

# 后端代码
COPY flypig/ ./flypig/

# 前端静态文件（从第一阶段复制）
COPY --from=frontend-builder /app/dist/ ./web/static/

EXPOSE 8321
CMD ["python", "-m", "flypig"]
```

## 三、Docker Compose

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
| **Redis** | SSE 事件跨实例广播（单机不需要，内存就够了） | 多实例水平扩展时 |
| **Prometheus + Grafana** | 监控 LLM token 消耗、API 延迟、错误率 | SaaS 上线前 |
| **Sentry** | 错误追踪 | SaaS 上线前 |
| **CDN** | 前端静态文件加速 | SaaS 上线前 |

---

> **当前阶段（单机版）**：docker-compose (api + db + nginx) 一键部署。CI/CD 只需 lint + test。
