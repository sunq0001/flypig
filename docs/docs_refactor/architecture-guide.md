# 架构导航索引

> **本文档是导航索引**，不是详细设计文档。
> 遇到问题 → 按分类查对应文档 → 在对应文档中查看关联链接。

## 核心原则

- **单向依赖**：Backend → Orchestration → Domain → Infrastructure
- **接口隔离**：领域层定义接口，基础设施层实现
- **DI 单点装配**：所有依赖在 Container 类里装配
- **每个文件一个职责**：不超过 200 行，一个类不超过 100 行
- **工具调用是 AI 的反射外延**：工具执行结果（含报错）原样返回 AI，不做任何预处理/计数/分类。AI 自行决定下一步

## 重构动机（为什么需要这样做）

### 当前痛点

| 问题 | 严重程度 | 影响 |
|-----|---------|------|
| `tools.py` ~820 行一个大文件 | 🔴 | 改一个函数要读完整文件 |
| `sandbox.py` ~1000 行一个大文件 | 🔴 | 沙箱配置、路径验证、Docker 管理混一起 |
| `server.py` ~780 行一个大文件 | 🔴 | 路由、配置、SSE、WebSocket 全在 |
| `index.html` ~2500 行单页 | 🔴 | Vue 组件、CSS、终端逻辑全在 |
| 全局变量散落 | 🔴 | 多请求状态混乱，测试无法隔离 |
| Agent 装配代码重复 3 处 | 🟡 | 改一个依赖要改三个地方 |
| PTY 注入链路 7 步 | 🔴 | AI→SSE→前端→API→终端→WS→PTY |
| 流式输出是模拟的 | 🟡 | setInterval 轮询，体验差 |
| 没有依赖注入 | 🟡 | 换模型需要改核心代码 |

### 重构收益

| 指标 | 当前 | 重构后 |
|------|------|--------|
| 单个文件最大行数 | ~2500 行 | ≤200 行 |
| Agent 装配代码重复 | 3 处 | 1 处（DI Container） |
| 模块间耦合 | 紧耦合 | 接口依赖 |
| 测试能力 | 几乎不可测试 | 接口可 Mock |
| 加新模型 | 改 agent.py、server.py | 加一个 ModelAdapter 实现 |
| 加新前端功能 | 改 2500 行 index.html | 加一个 .vue 组件 |

## AI 友好编码规范

### 命名规则

| 要素 | 规则 | 例子 |
|------|------|------|
| 包名 | 功能分组 | `domain/`, `infrastructure/` |
| 模块名 | 功能描述 | `tool_bash.py`, `mcp_loader.py` |
| 类名 | 大驼峰 | `ChatService`, `FileTreeScanner` |
| 函数名 | 小驼峰 | `check_permission()` |

### 文件结构规范

```python
"""一句话描述模块职责"""
# ── 标准库导入 ──
import asyncio
# ── 第三方库导入 ──
from quart import Quart
# ── 内部模块导入 ──
from ..domain.interfaces import IToolExecutor
# ── 常量 ──
_DEFAULT_TIMEOUT = 30
# ── 类定义 ──
class ToolBash:
    ...
```

## 问题导航

| 你想做什么 | 先看哪个文档 |
|-----------|------------|
| 了解整体架构设计 | `architecture-diagram.md` + `folder-tree.md` + `tech-stack.md` |
| 查看架构图 | `architecture-diagram.md` |
| 查看项目文件夹结构 | `folder-tree.md` |
| 查看技术选型 | `tech-stack.md` |
| 理解三种模式（Explore/Plan/Execute）的权限 | `mode-matrix.md` |
| 理解 LangGraph 节点、router、状态 | `langgraph-graph.md` |
| 查看所有 API 端点和 SSE 事件格式 | `api-reference.md` |
| 查看对话框交互设计和组件 | `frontend-arch.md` + `chat-ux.md` |
| 查看所有富交互组件清单和情绪价值设计 | `chat-ux.md` |
| 查看 SSE 事件类型（reasoning/change_plan 等） | `api-reference.md` → SSE 事件格式 |
| 查看前端架构和技术栈 | `frontend-arch.md` |
| 查看后端各层模块职责 | `backend-modules.md` |
| 查看 subprocess 执行策略和 task_log | `subprocess.md` |
| 查看工具定义和参数设计 | `tools.md` |
| 查看变更审查、Lint、对抗建议 | `adversarial-system.md` |
| 查看 Docker Compose 部署和 CI/CD | `operations.md` |
| 查看对话存储结构 | `mem_convStore.md` |
| 查看用量追踪（Token/Cost/缓存统计） | `mem_convStore_usage.md` |
| 查看迁移路线和 MVP 迭代 | `migration-roadmap.md` |
| 查看代码理解服务（搜索/知识图谱/向量库） | `folder-tree.md` → `infrastructure/search/` |
| 查看崩溃恢复/日志/数据迁移 | `resilience.md` |
| 查看许可激活/自动更新（P2 预留） | `resilience.md` → P1/P2 预留接口 |
| 查看导出/模型 fallback（P1 预留） | `resilience.md` → P1/P2 预留接口 |
| 查看开发者工具链规范 | `migration-roadmap.md` → Step 0 + `tech-stack.md` → 文档层次 |
| 查看 docstring 风格规范 | `migration-roadmap.md` → Step 0（Google 风格 + Ruff D + interrogate） |

## 快速定位：AI 应该看哪个文件

| 想改什么 | 先看哪个文件 |
|---------|------------|
| AI 对话流程 | `langgraph-graph.md` → `domain/agent/nodes.py` |
| 图构建/路由注册 | `langgraph-graph.md` → `orchestration/graph_factory.py` |
| 换 AI 模型 | `backend-modules.md` → `infrastructure/llm/` |
| 加工具 | `tools.md` → `infrastructure/tools/`（按 file/search/system/mcp 分组） |
| 改 SSE 事件 | `api-reference.md` → `backend/routes/chat.py` |
| 改前端消息渲染 | `frontend-arch.md` → `static_vite/src/components/chat/` |
| 改变更审查逻辑 | `adversarial-system.md` → `infrastructure/tools/review/tool_change_review.py` |
| 改代码规范检查 | `adversarial-system.md` → `infrastructure/tools/review/tool_lint.py` + `pyproject.toml` |
| 改变更评分逻辑 | `adversarial-system.md` → `domain/models/change_score.py` |
| 改模式配置(温度/工具) | `mode-matrix.md` → `domain/models/mode.py` |
| 改权限规则 | `backend-modules.md` → `infrastructure/policies/` + Casbin 策略文件 |
| 改会话持久化 | `mem_convStore.md` → `orchestration/conversation_store.py` |
| 改用量追踪 | `mem_convStore_usage.md` → `infrastructure/usage/` + `SqliteUsageTracker` |
| 断点恢复（关掉再开继续） | `api-reference.md` → `GET /api/sessions/<id>/restore` + `SessionService.restore()` |
| 改终端管理 | `subprocess.md` → `backend/terminal.py` |
| 工具安全限制（路径白名单） | `subprocess.md` → `infrastructure/tools/tool_bash.py` |
| 敏感信息检测 | `backend-modules.md` → `domain/agent/nodes.py`（chat_node 输出前） |
| 死循环检测 + 节点异常保护 | `langgraph-graph.md` → `domain/agent/nodes.py + router.py` |
| DI 容器装配 | `backend-modules.md` → `core/container.py` |
| LangGraph 节点逻辑 | `langgraph-graph.md` → `domain/agent/state.py + nodes.py + router.py + context.py` |
| 对抗建议生成 | `backend-modules.md` → `orchestration/suggestion_engine.py` |
| 钩子事件注册 | `backend-modules.md` → `orchestration/event_subscriptions.py` |
| 配置即代码 | `backend-modules.md` → YAML + `@dataclass ModelConfig` |
| 部署 / 运维 / CI/CD | `operations.md` → Docker Compose + GitHub Actions + 环境变量 |
| 数据类型规范 | `backend-modules.md` → `@dataclass` 替代 `dict` |
| 工具自动注册 | `tools.md` → `@tool()` 装饰器 |
| 工具调用幂等性 | `tools.md` → 各 `tool_*.py` 实现时注意 |
| 文件编辑策略 | `tools.md` → `FileEditStrategy` 策略模式 |
| SQLite WAL + trace_id | `backend-modules.md` → 健壮性章节 |
| 敏感信息检测 | `backend-modules.md` → 健壮性章节 |
| 优雅关闭 / 工具执行追踪 | `backend-modules.md` → 健壮性章节 |
| 对话存储与压缩 | `mem_convStore.md` + `short-term-memory.md` → `orchestration/conversation_store.py` |
| LangMem 长期记忆 | `mem_convStore.md`（LangMem 章节）→ 注册到 ToolNode |
| 建议反馈记录 | `adversarial-system.md`（建议反馈记录）→ `backend/routes/feedback.py` → `store.update_suggestion_feedback()` |
| 变更计划（改前预览） | `adversarial-system.md` → `change_plan` 节点，用户逐项批准后才执行 |
| 思考过程实时推流 | `subprocess.md` → chat_node 中 yield `reasoning` 事件 |
| 实时停止执行 | `subprocess.md` → `/api/agent/stop` + kill 子进程 |
| SSE 事件类型列表 | `api-reference.md` → SSE 事件格式（含 reasoning / change_plan） |
