# 迁移路线

> **关联文档**: 所有 `docs/docs_refactor/*.md`（执行到对应 Step 时参考对应文档）
> 改迁移顺序或 MVP 范围时，需同步检查所有子文档的依赖关系。

> **总原则**：重写而非重构。旧 `flypig/` 整体归档为 `flypig-archive/`（同级目录），新代码从零搭建，不依赖任何旧文件。

---

> **核心原则：前端即验证终端**。这是一个 AI Agent 项目，核心交互是**对话流**，不是 HTTP 响应。每轮后端只新增"当前轮次需要的最小功能"，前端量刚好够验证这一轮的工作流。每轮结束都**打开浏览器，和 AI 对话确认这一轮功能正常**，再开始下一轮。

---

## 第 0 轮：地基搭建（基础设施 + 骨架）

| Step | 名称 | 说明 |
|------|------|------|
| **Step -2** | 旧代码归档 | `flypig/` → `flypig-archive/` |
| **Step -1** | 建空骨架 | 按 `folder-tree.md` 创建目录 + 所有空文件 + docstring 模板 |
| **Step 0** | 开发者工具链 | MkDocs + mkdocstrings、Ruff D、interrogate、pre-commit |

### Step -2：旧代码归档

| 动作 | 说明 |
|------|------|
| 重命名 `flypig/` → `flypig-archive/` | 同级目录，原样保留全部旧文件，日后可回溯 |
| 验证：`flypig-archive/` 结构完整 | `flypig-archive/flypig/` 应包含所有旧代码 |

### Step -1：建空骨架

| 动作 | 说明 |
|------|------|
| 对照 `folder-tree.md` 创建所有目录 | `flypig/core/`, `flypig/domain/`, `flypig/orchestration/` … 共约 30+ 个子目录 |
| 在每个目录创建 `__init__.py` | 保证 Python 包可导入 |
| 创建所有空 `.py` 文件，每个文件顶部写 **5 段式 docstring 模板** | 见下方 docstring 模板规范 |
| 前端 `.vue/.js/.css` 文件只写文件头注释 | 不写 docstring 模板 |
| 创建根级配置文件 | `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `nginx.conf`, `mcp.json`, `.env.example`, `Makefile` |
| 新建 `tests/` 目录 | 含 `conftest.py`, `pytest.ini`, `unit/`, `integration/`, `fixtures/` |
| 新建 `frontend/` 骨架 | `frontend/static/` + `frontend/static_vite/` 含 `package.json`, `vite.config.js`, `index.html`, `src/main.js` |
| 新建 `scripts/` 目录 | `setup_env.py`（核心）+ `setup_env.bat` + `setup_env.sh`（入口）, `seed_data.py`, `migrate_db.py` |
| 验证：`python -c "import flypig"` | 确保包结构可导入，不报错 |

#### Docstring 模板规范

每个 `.py` 文件的 module-level docstring 格式如下：

```python
"""
[模块名]：一句话概括（用户/开发都能懂）

为什么做：需求场景。不说技术细节，让任何人读了一句话就能理解这个模块存在的意义。
实现方法：核心思路（1-3句）。简明说明「怎么实现的」，不写伪代码。
实现效果：用户在使用过程中能感知到的变化，以及什么样的体验。
技术栈：这个模块用到的关键库/技术（如 asyncio, sqlite3, httpx, pydantic 等）

层&依赖：domain / orchestration / infrastructure / backend 中的哪一层，能依赖谁不能依赖谁。
细节见文档：docs/docs_refactor/xxx.md → §章节 → 子标题
"""
```

**关键原则**：
- **前 3 段**：写给**人**看的——项目经理、未来的你、任何点开文件的人
- **技术栈**：一眼知道这个文件依赖什么，不用去翻 import 行
- **层&依赖**：写给**开发者和 AI**看的——防止 import 违规，保证分层纪律
- **细节见文档**：既是引用也是约束，"具体怎么做" 只写在 docs 里，docstring 和 docs 不脱节但互不重复
- **不留 `TODO: implement`**：骨架阶段 docstring 就是完整版本，不占位

### Step 0：开发者工具链搭建

| 动作 | 说明 |
|------|------|
| 安装 MkDocs + mkdocstrings | `pip install mkdocs mkdocstrings[python]` — 文档站框架，自动从 docstring 拉取 API 文档 |
| 初始化 MkDocs 配置 | `mkdocs new .` 后编辑 `mkdocs.yml`，nav 包含所有 `docs_refactor/*.md` + python 插件源 |
| 配置 Ruff D 规则 | `pyproject.toml` 中 `[tool.ruff.lint] select = ["D"]` + `convention = "google"` — 强制 Google 风格 docstring |
| 安装 interrogate | `pip install interrogate`，配置 `[tool.interrogate] fail-under = 80` — docstring 覆盖率门槛 ≥80% |
| 安装 pre-commit | `pip install pre-commit` + `pre-commit install`，创建 `.pre-commit-config.yaml` 含 ruff D + interrogate 钩子 |
| 验证工具链 | `ruff check flypig/` → 无 D 规则报错；`interrogate flypig/` → 覆盖率通过 |

### 开发环境热加载（开发期间全程使用）

前后端均使用热加载，改代码后无需手动重启。Docker 只用于最终部署（R7），开发期间在本地跑。

**启动方式**（创建 `scripts/dev.bat` + `dev.sh`）：

```bash
# 终端 1：后端热加载（uvicorn --reload 监听 .py 文件变更自动重启）
cd flypig && pip install -r requirements.txt && uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000

# 终端 2：前端热加载（Vite HMR 毫秒级替换 .vue/.js 模块）
cd flypig/frontend/static_vite && npm install && npm run dev -- --host
```

浏览器打开 `http://localhost:5173`，前端通过 Vite proxy 转发 `/api/*` 到 `localhost:8000`。

**热加载覆盖范围**：
- 后端 `.py` → uvicorn 监听到文件变更 → 自动重启进程（< 1 秒）
- 前端 `.vue` / `.js` / `.css` → Vite HMR 直接替换模块（毫秒级，不刷新页面）
- 配置文件 `.yaml` / `.toml` → uvicorn 重启也覆盖
- 新增 Python 依赖 → 在终端 `pip install` 后 uvicorn 自动重启（进程重启时加载新包）

---

> **核心原则**：每一轮结束时都**打开浏览器，和 AI 对话来验证**这一轮新增的功能。不使用 curl/pytest/http 客户端验证工作流。前端的量只够验证当轮功能即可，不多写。

---

## 第 1 轮：最小可对话（Round 1 — Hello, AI）

**目标**：浏览器里输入文字 → 看到 AI 流式回复。全过程通过**和 AI 对话验证**。

> 不写任何工具、记忆、context pipeline、模式区分。后端就是"接收 prompt → LLM stream → 推送 SSE"。

| 子步骤 | 后端写什么 | 前端写什么 | 验证 |
|--------|-----------|-----------|------|
| **R1.1** 骨架填充 | `core/*`（config, container, logging, events, app）+ `domain/interfaces/imodel.py` + `domain/interfaces/iagent.py` + `domain/exceptions.py` + `domain/config/config.py` + `domain/config/model_registry.py` | — | `pytest --collect-only` |
| **R1.2** Prompt 系统 | `domain/prompts/multirole_manager.py` + `domain/prompts/__init__.py` + `domain/prompts/roles/developer.md`（仅主 prompt，其余留空） | — | `python -c "from flypig.domain.prompts import *"` |
| **R1.3** LLM 适配器 | `infrastructure/llm/openai_adapter.py` | — | 写个最小脚本调通 LLM stream |
| **R1.4** 最小 LangGraph | `domain/models/message.py`（Message dataclass）+ `domain/agent/state.py` + `domain/agent/nodes.py`（仅 chat_node）+ `orchestration/graph_factory.py`（1 个节点 + 1 条边）+ `orchestration/chat_service.py`（简化版：接收→调 LLM→推 SSE） | — | 同上脚本调通 |
| **R1.5** 后端配置+路由 | `backend/server.py`（Quart 工厂 + 蓝图注册 + CORS）+ `backend/routes/config.py`（GET /api/config 返回全部运行时配置，POST 工作区/POST API Key）+ `backend/routes/chat.py` + `backend/routes/health.py` + `backend/sse_queue.py` + `__main__.py` | — | `curl -N localhost:8000/api/config` 看到完整配置 → `localhost:8000/api/health` 返回 OK |
| **R1.6** 最小前端+初始化 | `style/variables.css` + `style/base.css` | `index.html` + `main.js` + `App.vue`（onMounted 调 /api/config，无 workspace 显示 InitWizard，有则进聊天）+ `InitWizard.vue` + `WorkspaceStep.vue` + `ChatPanel.vue`（含 model-bar 模型下拉+⚙ API Key）+ `InputBox.vue` + `MessageList.vue` + `MessageItem.vue` + `useChat.js`（每次发送带 model 参数） | **浏览器：打开 → 无工作区 → 显示 InitWizard → 选目录 → 进聊天 → 输入"你好" → AI 流式回复** |

> **R1 测试剧本**（浏览器中执行，验证对话流）：
> ```
> 第1步：输入"你好，请介绍一下你自己"
>   → 应看到 AI 逐字流式回复（不是一次性输出，也不是刷屏）
>   → 检查点：打字机效果是否流畅？每 token 间隔是否均匀？
>
> 第2步（接上）：输入"用中文回复，说三句关于 Python 的话"
>   → 应看到 AI 在同一个对话上下文中回复，知道之前说了什么
>   → 检查点：多轮对话消息列表是否正常追加？滚动是否自动跟随？
>
> 第3步（接上）：输入"刚才我让你干嘛了"
>   → 应看到 AI 利用当前对话上下文中已有的消息历史做出回答
>   → 检查点：AI 是否能引用前两轮的具体内容？
> ```

**本轮结束后可验证的工作流**：
- 对话流：用户输入 → SSE 推流 → 前端流式渲染
- LLM 调用：prompt → model.stream → 逐 token 输出
- 前后端联调：Vite dev → 后端 API → SSE 消费

**本轮不做的功能**：
工具调用、记忆、context 压缩、多节点路由、ChoiceCard 等富卡片、模式区分、文件功能

---

## 第 2 轮：可见的工具调用（Round 2 — Tool Calls）

**目标**：AI 可以调用工具，前端能看到 tool_call 卡片和结果。

| 子步骤 | 后端写什么 | 前端写什么 | 验证 |
|--------|-----------|-----------|------|
| **R2.1** 工具系统 | `domain/interfaces/itool_executor.py` + `infrastructure/tools/executor.py` + `infrastructure/tools/utils.py` + `domain/interfaces/isearch.py` | — | `python -c "... 调一个工具"` |
| **R2.2** 文件工具 | `infrastructure/tools/file/tool_read.py` + `tool_write.py` + `tool_patch_file.py` + `tool_delete.py` + `tool_list_dir.py` | — | 同上 |
| **R2.3** 搜索+懒加载工具 | `infrastructure/tools/search/tool_search.py` + `tool_search_tools.py` + `tool_call_direct.py` + `infrastructure/search/search_grep.py`（实现 ISearch）+ `infrastructure/search/ast_parser.py`（P0 NoOp 实现 IASTParser）+ `infrastructure/search/lsp_diagnostics.py`（P0 NoOp 实现 ILspDiagnostics） | — | 同上 |
| **R2.4** 系统工具 | `infrastructure/tools/system/tool_bash.py` + `tool_git.py` + `tool_fetch_url.py` + `tool_datetime.py` + `tool_calc.py` + `tool_task.py` + `tool_task_manager.py` + `tool_extract_archive.py` | — | 同上 |
| **R2.5** 注册到 LangGraph | 更新 `nodes.py`（加 ToolNode）+ 更新 `graph_factory.py` + 更新 `core/container.py` | — | `curl` 看到 tool_call 事件 |
| **R2.6** 前端 tool 展示 | — | `ToolCallCard.vue`（显示工具名+参数+结果）+ `ThinkingIndicator.vue` + `CodeBlock.vue` + 更新 `MessageItem.vue` 支持 tool 消息 + `useEventRouter.js` | **浏览器：让 AI 搜索或读文件 → 看到 ToolCallCard 渲染** |

**本轮结束后可验证的工作流**：
- AI 自主决定调工具 → 触发 ToolNode → 结果返回 → 前端展示 ToolCallCard
- 文件读写工具链完整
- 搜索（grep）工具完整
- 系统工具（bash/url/日期/计算）完整

**本轮不做的功能**：
记忆（conversation_store）、多节点路由、ChoiceCard、ChangeReview、SuggestionCard、模式区分

> **R2 测试剧本**（浏览器中执行，验证工具调用）：
> ```
> 第1步：输入"读一下 __main__.py 的前 10 行"
>   → 应看到 ThinkingIndicator 闪烁 → ToolCallCard 展示工具名/参数/结果
>   → 检查点：工具调用的展示是否自然？是否打断了对话流？
>
> 第2步（接上）：输入"搜索包含 'container' 的文件"
>   → AI 应调 tool_search，展示匹配文件列表
>   → 检查点：搜索结果格式是否可读？
>
> 第3步（接上）：输入"在第一个匹配文件里找到 import 语句，读给我看"
>   → AI 应结合上一步搜索结果 + 调 tool_read 定位读取
>   → 检查点：AI 是否能利用上一步的工具输出作为下一步的上下文？
>
> 第4步（接上）：输入"给我算一下 2 的 10 次方"
>   → AI 应调 tool_calc，返回计算结果
>   → 检查点：简单计算工具是否正常工作？
>
> 第5步（回到默认上下文）：输入"刚才你帮我搜了啥？"
>   → AI 应引用前面的搜索结果（当前上下文内有工具调用记录）
>   → 检查点：工具调用的输出是否进入对话消息历史？
> ```

---

## 第 3 轮：记忆与多轮对话（Round 3 — Memory）

**目标**：AI 记得之前说过的话，切换会话后不丢失上下文。

| 子步骤 | 后端写什么 | 前端写什么 | 验证 |
|--------|-----------|-----------|------|
| **R3.1** 对话存储 | `domain/interfaces/iconversation_store.py` + `orchestration/conversation_store.py`（SQLite）+ `domain/models/session.py` | — | `pytest` 读写验证 |
| **R3.2** 会话服务 | `orchestration/session_service.py` + `orchestration/config_service.py` + `orchestration/event_subscriptions.py` | — | 测试创建/切换/恢复会话 |
| **R3.3** Context 压缩 | `domain/interfaces/icontext_pipeline.py` + `orchestration/context_pipeline.py` | — | 测试长对话压缩 |
| **R3.4** 注入 ChatService | 更新 `chat_service.py` + `core/container.py` 注入 IConversationStore + IContextPipeline + EventSubscriptions | — | `curl` 连续多轮对话 |
| **R3.5** 会话切换前端 | — | `Sidebar.vue`（会话列表）+ `useChat` 增加 session_id 管理 + `composables/useMessages.js` | **浏览器：多轮对话后发"刚才说了什么" → AI 记得** |

**本轮结束后可验证的工作流**：
- 多轮对话：AI 记得之前的上下文
- 会话切换：切换会话后恢复历史
- 长对话：context 压缩后不影响体验

**本轮不做的功能**：
ChoiceCard、ChangeReview、SuggestionCard、权限系统、用量追踪

> **R3 测试剧本**（浏览器中执行，验证记忆与多轮）：
> ```
> 第1步：输入"我的名字是张三"
>   → 应正常回复，消息写入消息历史
>
> 第2步（接上）：输入"我在做一个 Python 项目"
>   → 正常回复
>
> 第3步（接上）：输入"我叫什么名字？我在做什么项目？"
>   → AI 应能正确回答"张三"和"Python 项目"
>   → 检查点：多轮对话上下文是否完整？
>
> 第4步：刷新页面（会话丢失场景）
>   → 左侧 Sidebar 应显示已有会话列表
>   → 点击刚才的会话 → 历史消息恢复
>   → 输入"我刚才在做什么？"
>     → AI 应正确引用会话历史中的内容
>     → 检查点：会话持久化和恢复是否完整？
>
> 第5步（长对话压力测试）：连续输入 20 条短消息（如"说个笑话" × 20）
>   → 观察第 15 轮后的回复质量是否有明显下降
>   → 检查点：context 压缩是否生效？长对话是否造成质量退化？
> ```

---

## 第 4 轮：富交互卡片（Round 4 — Rich Cards）

**目标**：AI 出选择题、展示 diff、对抗建议——前端渲染富卡片。

| 子步骤 | 后端写什么 | 前端写什么 | 验证 |
|--------|-----------|-----------|------|
| **R4.1** ChoiceCard 后端 | `domain/interfaces/itool_executor.py`（ask_choice 工具）+ `infrastructure/tools/interact/tool_ask_choice.py` + `domain/agent/nodes.py`（ask_choice_node） | — | `curl` 触发 choice 事件 |
| **R4.2** ChoiceCard 前端 | — | `ChoiceCard.vue` + 更新 `EventRouter` + `useEventRouter.js` | **浏览器：AI 出选择题 → 看到 ChoiceCard** |
| **R4.3** 变更审查后端 | `infrastructure/tools/review/`（tool_change_review.py + tool_lint.py + tool_change_score.py）+ `domain/models/change_score.py` + `domain/agent/nodes.py`（review_node + lint_node） | — | `curl` 触发 diff + lint 事件 |
| **R4.4** 变更审查前端 | — | `DiffViewer.vue` + `ChangeReviewCard.vue` + `CodeBlock.vue` | **浏览器：AI 改文件 → 看到 DiffViewer 卡片** |
| **R4.5** 对抗建议后端 | `orchestration/suggestion_engine.py` + `domain/agent/nodes.py`（suggest_node） | — | `curl` 触发 suggest 事件 |
| **R4.6** 对抗建议前端 | — | `SuggestionCard.vue` | **浏览器：AI 提建议 → 看到 SuggestionCard** |

**本轮结束后可验证的工作流**：
- AI 出选择题 → ChoiceCard → 用户选择 → AI 继续
- AI 改文件 → DiffViewer → 用户确认 → 写入
- AI 审查+打分 → 对抗建议 → 用户反馈

**本轮不做的功能**：
权限系统（Casbin）、用量追踪、Docker 沙箱

> **R4 测试剧本**（浏览器中执行，验证富卡片）：
> ```
> 第1步：输入"我想了解一下这个项目的结构，我该从哪里下手？"
>   → AI 应出 ChoiceCard，展示几个探索方向供选择
>   → 检查点：ChoiceCard 的选项是否可点击？点击后 AI 是否按选择继续？
>
> 第2步（文件变更场景）：输入"帮我创建一个 test.js 文件，里面写一个冒泡排序"
>   → AI 应创建文件，然后触发 ChangeReviewCard + DiffViewer 展示变更
>   → 检查点：DiffViewer 是否清晰展示新增的代码行？
>
> 第3步（接上）：输入"检查一下代码质量"
>   → AI 应调 tool_lint 检查代码 → 展示 Lint 结果
>   → 检查点：lint 卡片是否展示错误行和解释？
>
> 第4步（接上）：输入"你觉得这段代码有什么改进空间？"
>   → AI 应生成对比建议 → 展示 SuggestionCard
>   → 检查点：SuggestionCard 是否可读？是否提供了有价值的建议？
> ```

---

## 第 5 轮：权限与系统功能（Round 5 — Permissions & System）

**目标**：权限校验、用量追踪、终端面板。

| 子步骤 | 后端写什么 | 前端写什么 | 验证 |
|--------|-----------|-----------|------|
| **R5.1** 权限系统 | `infrastructure/policies/`（model.conf + policy.csv + casbin_setup.py + permission_checker.py）+ `orchestration/policy_service.py` | — | `pytest` Casbin 矩阵测试 |
| **R5.2** 注入 ChatService | 更新 `chat_service.py` + `core/container.py` policy check | — | 对话中触发 allow/ask/deny |
| **R5.3** 用量追踪 | `domain/interfaces/iusage_tracker.py` + `infrastructure/usage/`（sqlite_tracker.py + pricing.py + usage_handler.py）+ `orchestration/usage_tracker_service.py` | — | `pytest` + `curl` 验证记录 |
| **R5.4** 文件监控路由 | `backend/routes/files.py` + `backend/file_watcher.py` + `backend/routes/upload.py` | — | `curl` 文件列表/上传 |
| **R5.5** 剩余路由补全 | `backend/routes/config.py` + `sessions.py` + `rollback.py` + `agent_routes.py` + `history.py` + `tasks.py` + `feedback.py` + `backend/routes/usage.py` | — | `curl` 各端点返回正常 |
| **R5.6** 前端文件树 | — | `FileTree.vue` + `FileTreeNode.vue` + `useFileTree.js` + `components/layout/MainLayout.vue` + `ResizeHandle.vue` | **浏览器：看到文件树，点击展开** |
| **R5.7** 终端面板 | `infrastructure/terminal.py` + `backend/terminal.py` | `TerminalPanel.vue` + `XtermViewer.vue` + `OutputViewer.vue` + `useTerminal.js` + `lib/xterm-setup.js` | **浏览器：终端面板有 xterm.js 渲染** |
| **R5.8** 前端完整布局 | — | `components/common/LoadingSpinner.vue` + `MarkdownRender.vue` + `StatusBar.vue` + `ThemeSwitcher.vue` + `composables/useLayout.js` + `composables/useTheme.js` + `composables/useMarkdownRender.js` + `style/terminal-themes.css` + `theme-cyberpunk.css` + `theme-cute.css` | **浏览器：布局完善、主题切换正常** |

**本轮结束后可验证的工作流**：
- 权限校验：AI 尝试删除关键文件 → 弹出确认
- 用量记录：对话后看到 token 消耗
- 文件树：左侧面板展示项目文件
- 终端面板：用户手动操作终端

> **R5 测试剧本**（浏览器中执行，验证权限/用量/布局）：
> ```
> 第1步：输入"删除 src/main.js 文件"
>   → 权限系统应触发 ask（请求用户确认），弹出确认框
>   → 检查点：确认框是否正常弹出？点允许后是否执行？点拒绝后是否不执行？
>
> 第2步：切换左侧面板到文件树 Tab
>   → 看到项目的文件树结构，点击文件夹展开/收起
>   → 检查点：文件树是否正确展示目录结构？
>
> 第3步：看底部状态栏
>   → 应显示当前模型、token 用量、会话信息
>   → 检查点：用量信息是否随对话更新？
>
> 第4步：切换主题
>   → 应看到 UI 主题切换为暗色/亮色/赛博朋克等风格
>   → 检查点：主题切换是否流畅？是否有明显闪烁？
> ```

## 第 6 轮：高级特性（Round 6 — Advanced）

**目标**：模式区分、Mermaid 图表、MCP 集成、Docker 沙箱。

| 子步骤 | 后端写什么 | 前端写什么 | 验证 |
|--------|-----------|-----------|------|
| **R6.1** 模式区分 | `domain/models/mode.py` + `domain/models/task.py`（TaskItem dataclass）+ `domain/agent/context.py`（Explore/Plan/Execute）+ `domain/agent/router.py`（条件路由） + 补齐 `domain/prompts/roles/reviewer.md` + `tester.md` + `architect.md` + `documenter.md` | — | **浏览器：切模式后工具集会变** |
| **R6.2** Mermaid 渲染 | 升级 SSE 事件支持 chart/text 等 | `MermaidDiagram.vue` + `ChartView.vue` + `InlinePreview.vue` + `LivePreview.vue` + `DataTable.vue` + `FormGenerator.vue` + `DashboardWidget.vue` + `CommandCard.vue` + `MemoryBubble.vue` + `ImagePreview.vue` + `FilePreview.vue` | **浏览器：AI 画图 → 看到渲染** |
| **R6.3** MCP 集成 | `infrastructure/tools/mcp/`（tool_mcp_loader.py + tool_mcp_manager.py）+ `domain/interfaces/imodel.py`（MCP 注册扩展）+ `mcp.json` 配置 | — | **浏览器：加载 MCP → 工具变多** |
| **R6.4** Docker 沙箱 | `infrastructure/sandbox/`（sandbox_config.py + path_validator.py + sandbox_manager.py + builder.py） | `ToolCallCard` 加沙箱/本地标识 | **浏览器：沙箱运行 → 看到沙箱标识** |
| **R6.5** Checkpoint + 恢复 | `orchestration/git_checkpoint_manager.py` + `orchestration/summary_generator.py` + `infrastructure/hooks.py` + `infrastructure/process_manager.py` | `RecoveryDialog.vue` + `TaskHistoryDialog.vue` + `CommandPalette.vue` + `composables/useCommandPalette.js` + `composables/useEditor.js` + `composables/useTasks.js` + `composables/useDraft.js` + `composables/useFileDrop.js` + `composables/useUxEnhancements.js` + `lib/monaco-setup.js` + `lib/sfc-compiler.js` | **浏览器：中断后恢复 → 看到 RecoveryDialog** |
| **R6.6** 多模型适配 | `infrastructure/llm/anthropic.py` + `infrastructure/llm/local.py` + `scripts/seed_data.py` + `scripts/migrate_db.py` | — | **浏览器：切换模型后对话正常** |

---

## 第 7 轮：容器化 + 部署（Round 7 — Ship）

**目标**：Docker Compose 一键部署，全链路回归验证。

| 动作 | 说明 |
|------|------|
| 创建 `Dockerfile` | 应用容器化 |
| 完善 `docker-compose.yml` | api + nginx 编排 |
| 创建 `nginx.conf` | 反向代理 + 静态文件 + SSL |

> **R6 测试剧本**（浏览器中执行，验证高级特性）：
> ```
> 第1步（模式切换）：切换到 Plan 模式，输入"帮我重构一下文件结构"
>   → AI 应生成文件变更计划，调用工具前先输出方案
>   → 切换到 Execute 模式，输入"执行刚才的重构方案"
>     → 检查点：模式切换后 AI 行为是否变化？工具可用性是否受约束？
>
> 第2步（Mermaid）：输入"画一个用户登录的流程图"
>   → AI 应生成 Mermaid 代码 → 前端渲染为流程图
>   → 检查点：Mermaid 渲染是否正常？是否支持交互（缩放/点击）？
>
> 第3步（MCP）：加载一个 MCP 服务器（如 filesystem），然后说"用 MCP 列一下文件"
>   → AI 应调用 MCP 工具而非内置 tool_list_dir
>   → 检查点：MCP 工具是否注册成功？调用时是否显示 MCP 标识？
>
> 第4步（多模型）：在设置中切换到 Claude 模型，重复 R1 测试剧本
>   → 两个模型应输出不同风格的回答
>   → 检查点：模型切换是否生效？API Key 管理是否正确？
> ```

**验证**：`docker compose up` → 浏览器访问 → 和 AI 对话确认全链路正常。

---

## 物理文件映射（完整目标清单）

### 文件→Round 归位表（★ MVP 文件标注归属，☆ P1/P2 预留不列）

| Round | 层 | 文件 |
|-------|----|------|
| **R1** | core | `core/*`（5 个）、`__main__.py` |
| | config | `config.yaml`、`.env.example` |
| | domain/interfaces | `imodel.py`、`iagent.py` |
| | domain/config | `config.py`、`model_registry.py` |
| | domain/prompts | `multirole_manager.py`、`roles/developer.md` |
| | domain/agent | `state.py`、`nodes.py`（chat_node 初版） |
| | domain/models | `message.py` |
| | domain | `exceptions.py` |
| | orchestration | `graph_factory.py`（初版）、`chat_service.py`（初版） |
| | infrastructure/llm | `openai_adapter.py` |
| | backend | `server.py`、`routes/config.py`、`routes/chat.py`、`routes/health.py`、`sse_queue.py` |
| | frontend | `App.vue`、`InitWizard.vue`、`WorkspaceStep.vue`、`ChatPanel.vue`、`MessageList.vue`、`MessageItem.vue`、`InputBox.vue`、`useChat.js`、`style/variables.css`、`style/base.css` |
| | config | `vite.config.js`、`package.json`、`.env.example` |
| |
| **R2** | domain/interfaces | `itool_executor.py`、`isearch.py` |
| | infrastructure/tools | `executor.py`、`utils.py`、`file/*`（5 个）、`search/tool_search.py`、`tool_search_tools.py`、`tool_call_direct.py`、`system/*`（8 个） |
| | infrastructure/search | `search_grep.py`、`ast_parser.py`、`lsp_diagnostics.py` |
| | domain/agent | `nodes.py`（加 ToolNode） |
| | orchestration | `graph_factory.py`（更新）、`core/container.py`（更新） |
| | frontend | `ToolCallCard.vue`、`ThinkingIndicator.vue`、`CodeBlock.vue`、`useEventRouter.js`、`composables/useChat.js`（更新） |
| |
| **R3** | domain/interfaces | `iconversation_store.py`、`icontext_pipeline.py` |
| | domain/models | `session.py` |
| | orchestration | `conversation_store.py`、`session_service.py`、`config_service.py`、`event_subscriptions.py`、`context_pipeline.py`、`chat_service.py`（更新）、`core/container.py`（更新） |
| | backend/routes | `sessions.py` |
| | frontend | `Sidebar.vue`、`useMessages.js` |
| |
| **R4** | infrastructure/tools | `interact/tool_ask_choice.py`、`review/*`（3 个） |
| | domain/models | `change_score.py` |
| | domain/agent | `nodes.py`（加 ask_choice/review/lint/suggest node） |
| | orchestration | `suggestion_engine.py` |
| | frontend | `ChoiceCard.vue`、`DiffViewer.vue`、`ChangeReviewCard.vue`、`SuggestionCard.vue`、`EventRouter`（更新） |
| |
| **R5** | infrastructure/policies | `model.conf`、`policy.csv`、`casbin_setup.py`、`permission_checker.py` |
| | infrastructure/usage | `sqlite_tracker.py`、`pricing.py`、`usage_handler.py` |
| | infrastructure | `terminal.py` |
| | orchestration | `policy_service.py`、`usage_tracker_service.py`、`chat_service.py`（更新） |
| | backend | `routes/files.py`、`routes/upload.py`、`routes/config.py`、`routes/rollback.py`、`routes/agent_routes.py`、`routes/history.py`、`routes/tasks.py`、`routes/feedback.py`、`routes/usage.py`、`routes/sessions.py`（完善）、`file_watcher.py`、`terminal.py` |
| | frontend | `MainLayout.vue`、`ResizeHandle.vue`、`StatusBar.vue`、`FileTree.vue`、`FileTreeNode.vue`、`TerminalPanel.vue`、`XtermViewer.vue`、`OutputViewer.vue`、`MarkdownRender.vue`、`LoadingSpinner.vue`、`ThemeSwitcher.vue`、`useFileTree.js`、`useTerminal.js`、`useLayout.js`、`useTheme.js`、`useMarkdownRender.js`、`lib/xterm-setup.js`、`style/*.css` |
| |
| **R6** | domain/models | `mode.py`、`task.py` |
| | domain/agent | `context.py`、`router.py` |
| | domain/prompts | `roles/reviewer.md`、`tester.md`、`architect.md`、`documenter.md` |
| | infrastructure/sandbox | `sandbox_config.py`、`path_validator.py`、`sandbox_manager.py`、`builder.py` |
| | infrastructure/tools/mcp | `tool_mcp_loader.py`、`tool_mcp_manager.py` |
| | infrastructure/llm | `anthropic.py`、`local.py` |
| | infrastructure | `hooks.py`、`process_manager.py` |
| | orchestration | `git_checkpoint_manager.py`、`summary_generator.py`、`graph_config.yaml` |
| | scripts | `seed_data.py`、`migrate_db.py` |
| | frontend | `MermaidDiagram.vue`、`ChartView.vue`、`InlinePreview.vue`、`LivePreview.vue`、`DataTable.vue`、`FormGenerator.vue`、`DashboardWidget.vue`、`CommandCard.vue`、`MemoryBubble.vue`、`ImagePreview.vue`、`FilePreview.vue`、`RecoveryDialog.vue`、`TaskHistoryDialog.vue`、`CommandPalette.vue`、`useCommandPalette.js`、`useEditor.js`、`useTasks.js`、`useDraft.js`、`useFileDrop.js`、`useUxEnhancements.js`、`lib/monaco-setup.js`、`lib/sfc-compiler.js`、`mcp.json` |
| |
| **R7** | config | `Dockerfile`、`docker-compose.yml`、`nginx.conf` |
| | 测试 | `tests/*`（全部 12 个文件，贯穿各 Round 但 R7 时全部补完） |
| | tools | `scripts/setup_env.py`、`setup_env.bat`、`setup_env.sh` |

**注意**：上表不列 `__init__.py`（每个包目录都需要，贯穿全程）。所有 ☆ P1/P2 预留接口在任一 Round 不实现，仅保留 docstring 骨架。

---

## MVP 迭代建议

| 轮次 | Rounds | 核心验证方式 | 可演示功能 | 不做 |
|------|--------|------------|-----------|------|
| **MVP 1** | -2 → R1 | **浏览器：和 AI 对话** | 用户输入→SSE→AI 流式回复 | 工具调用、记忆、富卡片 |
| **MVP 2** | R2 → R3 | **浏览器：和 AI 对话** | 工具调用卡、多轮记忆、文件树 | 对抗建议、Mermaid、Docker |
| **MVP 3** | R4 → R5 | **浏览器：和 AI 对话** | ChoiceCard、DiffViewer、权限、用量 | MCP、Sandbox |
| **MVP 4** | R6 → R7 | **浏览器：和 AI 对话** | 模式区分、Mermaid、MCP、Docker | — |

**核心不变**：所有 MVP 的验证方式都是"打开浏览器，和 AI 说话"，没有例外。

## DevOps 架构

> **详见独立文档 `operations.md`**：Docker Compose 配置、CI/CD 流水线、环境变量、健康检查、SaaS 扩展。
