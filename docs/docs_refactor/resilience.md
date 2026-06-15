# 韧性系统：崩溃恢复 | 日志系统 | 数据迁移

> **关联文档**: `backend-modules.md`（TurnCheckpointHook）、`operations.md`（备份策略）、`architecture-guide.md`（总览）
> 改崩溃恢复逻辑或日志配置时，需同步检查 backend-modules.md 中的 TurnCheckpointHook 和 chat_node 实现。

## 一、崩溃恢复系统

### 问题

用户中途关掉 FlyPig（断电、进程 kill、浏览器关闭），正在进行的对话轮次丢失。当前 `chat_node` 只在**整轮结束**后存 `save_turn()`，工具调用已修改了文件但没来得及 checkpoint。

### 方案：每工具调用后 checkpoint（默认启用）

将 TurnCheckpointHook 从"可选"改为**默认启用**：

```python
# orchestration/chat_service.py
# ChatService.__init__() 中注册

@hook("tool:after", priority=50)
class TurnCheckpointHook:
    """每调完一个工具就 checkpoint 一次，防止崩溃丢数据"""

    async def on_event(self, ctx: HookContext):
        store = Container.get("conversation_store")
        state = ctx.state  # 当前 AgentState
        await store.save_checkpoint(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            partial=True,  # 标记为"未完成轮次"
            messages=state["messages"],
            tool_results=ctx.data.get("tool_results", []),
        )
```

### 启动恢复流程

进程启动时检测是否有 `partial=True` 的轮次：

```python
# __main__.py 启动时

async def check_recovery():
    store = Container.get("conversation_store")
    partial_turn = await store.get_last_partial_turn()
    if partial_turn:
        # 抛给 UI 层显示恢复提示
        return {
            "type": "recovery",
            "session_id": partial_turn.session_id,
            "turn_id": partial_turn.turn_id,
            "summary": "检测到上一轮未正常结束",
            "preview": partial_turn.summary,
        }
    return None
```

### CheckpointStore 扩展

```sql
-- checkpoints 表新增 partial 字段
ALTER TABLE checkpoints ADD COLUMN partial INTEGER DEFAULT 0;
-- partial=1 表示"未完成轮次的中间状态"
```

### 前端恢复提示

```
┌─────────────────────────────────────────┐
│ ⚠️ 检测到上次对话未正常结束               │
│                                          │
│ 在 turn_5 时中断，已执行工具调用:          │
│  ✅ write_file auth.py                    │
│  ✅ tool_bash pip install ...             │
│                                          │
│  [继续对话] [放弃中断的轮次]               │
└─────────────────────────────────────────┘
```

### 前端防误刷

输入框内容每次变更写入 localStorage：

```javascript
// composables/useChat.js 增强
const DRAFT_KEY = `flypig_draft_${sessionId}`

watch(input, debounce((val) => {
    localStorage.setItem(DRAFT_KEY, val)
}, 500))

onMounted(() => {
    const draft = localStorage.getItem(DRAFT_KEY)
    if (draft) {
        input.value = draft  // 恢复草稿
        showRestoreToast("已恢复上次未发送的输入")
    }
})
```

---

## 二、日志系统

### 原则

- 所有日志写到文件，不只看 stdout（终端关了也能查）
- 日志自动轮转，不撑爆磁盘
- 用户可通过 `--debug` CLI 参数开启 debug 日志
- 日志路径：`~/.flypig/logs/`

### 技术选型：loguru

不自己搭 logging 框架，用 `loguru`（`pip install loguru`）：

| 对比 | Python logging | loguru |
|------|--------------|--------|
| 配置代码 | 10+ 行模板 | 1 行 `add(sink)` |
| 日志轮转 | 需 RotatingFileHandler | 内置 `rotation="10 MB"` |
| 格式 | 手写 Formatter | 内置彩色 + 结构化 |
| 异常追踪 | 需 `exc_info=True` | 自动捕获 |
| 性能 | — | 异步 writer，不阻塞主线程 |

### 初始化

```python
# __main__.py 或 flypig/__init__.py

import sys
from loguru import logger
from pathlib import Path

_LOG_DIR = Path.home() / ".flypig" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

def init_logging(debug: bool = False):
    """初始化日志系统"""
    # 移除默认 handler
    logger.remove()

    # 文件日志（自动轮转 + 压缩）
    logger.add(
        _LOG_DIR / "flypig_{time:YYYY-MM-DD}.log",
        rotation="10 MB",         # 每个文件 10MB
        retention="30 days",      # 保留 30 天
        compression="gz",         # 自动 gzip 压缩旧日志
        level="DEBUG" if debug else "INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<7} | {name}:{function}:{line} | {message}",
        enqueue=True,             # 异步写入，不阻塞主线程
        backtrace=True,           # 异常时输出完整堆栈
    )

    # 控制台日志（带颜色）
    logger.add(
        sys.stderr,
        level="DEBUG" if debug else "INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | <cyan>{name}</cyan> | {message}",
        colorize=True,
    )

    logger.info("日志系统初始化完成，日志目录: {}", _LOG_DIR)
```

### CLI 参数

```python
# __main__.py
import argparse

parser = argparse.ArgumentParser("FlyPig")
parser.add_argument("--debug", action="store_true", help="开启 debug 日志")
parser.add_argument("--log-dir", default=None, help="日志目录（默认 ~/.flypig/logs/）")
args = parser.parse_args()

if args.log_dir:
    _LOG_DIR = Path(args.log_dir)
init_logging(debug=args.debug)
```

### trace_id 集成

```python
# 所有关键路径走 logger 而不是 print
# 结合已有的 trace_id:

logger.info("[trace={}] 用户输入: {}", trace_id, user_input[:100])
logger.debug("[trace={}] tool_call: {}({})", trace_id, tool_name, args)

# 异常时自动捕获
try:
    result = await tool.execute()
except Exception:
    logger.exception("[trace={}] 工具执行异常: {}", trace_id, tool_name)
    # logger.exception 自动输出完整堆栈
```

### 日志目录结构

```
~/.flypig/logs/
├── flypig_2026-06-13.log      ← 今天的日志
├── flypig_2026-06-12.log.gz   ← 自动压缩的历史
├── flypig_2026-06-11.log.gz
└── ...                         ← 保留 30 天
```

### 异常报告

用户遇到问题时可以：

```bash
# 用户发来的排查命令
cat ~/.flypig/logs/$(date +%Y-%m-%d).log | grep "ERROR"

# 或导出完整日志
tar czf flypig-logs.tar.gz ~/.flypig/logs/
```

---

## 三、数据迁移（Schema 版本管理）

### 问题

SQLite schema 随版本变化。v1.0 的 `tasks` 表在 v1.1 可能新增 `priority` 列，`conversations.db` / `usage.db` / `langgraph.db` 三个库都需要管理版本。

### 方案：`_SCHEMA_VERSION` + 自动迁移

每个数据库初始化时创建 `_meta` 表记录当前 schema 版本：

```python
_SCHEMA_VERSION = 2  # 当前版本号，每改 schema +1

_MIGRATIONS = {
    # version_from: (sql_upgrade_statement, version_to)
    1: (
        # v1 → v2: tasks 表新增 priority 列
        "ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'medium'",
        2,
    ),
}

def _init_db(self):
    with sqlite3.connect(self.db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")

        # 1. 建 _meta 表（记录 schema 版本）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # 2. 获取当前版本
        row = conn.execute(
            "SELECT value FROM _meta WHERE key = 'schema_version'"
        ).fetchone()
        current_version = int(row[0]) if row else 0

        # 3. 创建初始表（首次启动）
        if current_version == 0:
            self._create_initial_tables(conn)
            conn.execute(
                "INSERT OR REPLACE INTO _meta (key, value) VALUES ('schema_version', ?)",
                (str(_SCHEMA_VERSION),)
            )
            logger.info("数据库初始化完成，schema v{}", _SCHEMA_VERSION)
            return

        # 4. 自动迁移（逐版本升级）
        if current_version < _SCHEMA_VERSION:
            for v_from, (sql, v_to) in sorted(_MIGRATIONS.items()):
                if current_version == v_from:
                    conn.execute(sql)
                    conn.execute(
                        "UPDATE _meta SET value = ? WHERE key = 'schema_version'",
                        (str(v_to),)
                    )
                    current_version = v_to
                    logger.info("数据库迁移: schema v{} → v{}", v_from, v_to)
            logger.info("数据库迁移完成，当前 schema v{}", _SCHEMA_VERSION)

        # 5. 如果版本号比代码新（降级了），警告但不阻止
        if current_version > _SCHEMA_VERSION:
            logger.warning(
                "数据库 schema v{} 高于代码支持的 v{}，可能不兼容",
                current_version, _SCHEMA_VERSION
            )
```

### 三库统一管理

```
conversations.db → SqliteConversationStore._init_db() 管理自身 schema
usage.db         → SqliteUsageTracker._init_db()      管理自身 schema
langgraph.db     → LangGraph Checkpointer 自身管理（LangGraph SDK 负责）
```

### 降级保护

用户误装了旧版本 FlyPig 打开新版本数据库：

```python
# 启动时检测版本
@hook("app:startup", priority=99)
class SchemaVersionHook:
    async def on_event(self, ctx):
        for db_name, db_path in [
            ("conversations", "data/conversations.db"),
            ("usage", "data/conversations.db"),
        ]:
            if Path(db_path).exists():
                version = self._get_version(db_path)
                if version > _SCHEMA_VERSION:
                    logger.error(
                        "{} 数据库版本 v{} > 当前代码 v{}，请升级 FlyPig",
                        db_name, version, _SCHEMA_VERSION
                    )
                    # 前端弹窗提示升级
                    yield {
                        "type": "notification",
                        "severity": "error",
                        "title": "数据库版本不兼容",
                        "content": f"{db_name}.db 由更高版本的 FlyPig 创建，请升级当前程序后再打开。",
                    }
```

---

## 四、已预留接口（P1/P2）

以下接口只在文档中定义，MVP 阶段使用 NoOp 实现。

### LicenseService（P2 — 许可激活）

```python
# domain/interfaces/ilicense_service.py
class ILicenseService(ABC):
    """许可激活接口"""

    @abstractmethod
    async def check_license(self) -> LicenseStatus:
        """返回当前许可状态"""

    @abstractmethod
    async def activate(self, license_key: str) -> ActivationResult:
        """激活产品，返回成功/失败信息"""

    @abstractmethod
    async def deactivate(self) -> bool:
        """在当前设备上注销"""

@dataclass
class LicenseStatus:
    is_valid: bool
    license_type: str = "trial"         # trial / pro / enterprise
    days_remaining: int = 0
    expires_at: str | None = None

@dataclass
class ActivationResult:
    success: bool
    message: str
    machine_id: str | None = None

class NoOpLicenseService(ILicenseService):
    """MVP 阶段 — 永远返回「已激活」"""
    async def check_license(self) -> LicenseStatus:
        return LicenseStatus(is_valid=True, license_type="pro", days_remaining=36500)
    async def activate(self, key: str) -> ActivationResult:
        return ActivationResult(True, "已激活（MVP 模式）", "noop-mvp")
    async def deactivate(self) -> bool:
        return True
```

### UpdateService（P2 — 自动更新）

```python
# domain/interfaces/iupdate_service.py
class IUpdateService(ABC):
    """自动更新接口"""

    @abstractmethod
    async def check_update(self) -> UpdateInfo | None:
        """检查是否有新版本"""

    @abstractmethod
    async def download_and_install(self, update_id: str) -> bool:
        """下载并安装更新"""

    @abstractmethod
    async def get_update_history(self) -> list[UpdateRecord]:
        """获取更新历史"""

@dataclass
class UpdateInfo:
    version: str
    release_date: str
    changelog: str
    download_url: str
    checksum: str
    size_mb: float
    is_forced: bool = False  # 强制更新

@dataclass
class UpdateRecord:
    version: str
    installed_at: str
    success: bool

class NoOpUpdateService(IUpdateService):
    """MVP 阶段 — 永远返回「已是最新」"""
    async def check_update(self) -> UpdateInfo | None:
        return None
    async def download_and_install(self, update_id: str) -> bool:
        return False
    async def get_update_history(self) -> list[UpdateRecord]:
        return []
```

### ExportService（P1 — 导入导出）

```python
# orchestration/export_service.py
class ExportService:
    """导入/导出服务（P1 实现具体逻辑，P0 只定义端点）"""

    async def export_chat(self, session_id: str, format: str = "markdown") -> str:
        """导出对话为 Markdown/JSON"""
        raise NotImplementedError("P1 实现")

    async def export_tasks(self, session_id: str) -> str:
        """导出任务列表为 JSON"""
        raise NotImplementedError("P1 实现")

    async def import_from_claude(self, path: str) -> str:
        """从 Claude Code 导入"""
        raise NotImplementedError("P2 实现")

    async def import_from_codebuddy(self, path: str) -> str:
        """从 CodeBuddy 导入"""
        raise NotImplementedError("P2 实现")
```

### MultiModel Fallback（P1 — 多模型自动切换）

```python
# orchestration/model_fallback_service.py
class ModelFallbackService:
    """
    多模型自动 fallback 策略。
    当主模型（如 DeepSeek）连续失败时，自动切换到备选模型（如 Qwen）。
    P0: 不做自动切换，仅记录错误
    P1: 实现自动 fallback
    """

    def __init__(self):
        self._model_priority = ["deepseek-chat", "qwen-plus", "glm-4"]
        self._consecutive_failures: dict[str, int] = {}

    def get_available_models(self) -> list[str]:
        """返回按优先级排序的可用模型列表"""
        # P0: 只返回当前配置的模型
        return [Container.get("config").default_model]

    async def fallback_if_needed(self, model_name: str, error: Exception) -> str | None:
        """
        检测是否需要 fallback，返回备选模型名。
        P0: 不切换，仅记录
        """
        logger.warning("模型 [{}] 失败: {}（P0 阶段不自动 fallback）", model_name, error)
        return None
```

### i18n 多语言（P2）

```text
P0/P1: 所有 UI 文本硬编码中文（已经满足国内用户）
P2:    vue-i18n + locale JSON 文件，按 `navigator.language` 自动切换
       配置中的 persona 文本（需求分析师/规划师/执行者）也走 i18n
```

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `docs/docs_refactor/resilience.md` | **新增** | 本文 |
| `domain/interfaces/ilicense_service.py` | 新增 | 许可激活接口 + NoOp |
| `domain/interfaces/iupdate_service.py` | 新增 | 自动更新接口 + NoOp |
| `orchestration/export_service.py` | 新增 | 导出服务（P1 实现） |
| `orchestration/model_fallback_service.py` | 新增 | 模型 fallback 服务 |
| `orchestration/chat_service.py` | 修改 | 默认注册 TurnCheckpointHook |
| `orchestration/conversation_store.py` | 修改 | 添加 _SCHEMA_VERSION 迁移+ partial checkpoint |
| `infrastructure/usage/sqlite_tracker.py` | 修改 | 添加 _SCHEMA_VERSION 迁移 |
| `__main__.py` | 修改 | 添加 --debug 参数 + init_logging() + 恢复检测 |
| `composables/useChat.js` | 修改 | 添加 localStorage 草稿恢复 |
| `components/common/RecoveryDialog.vue` | 新增 | 崩溃恢复弹窗 |
