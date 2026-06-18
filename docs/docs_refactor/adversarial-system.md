# 对抗体系：审查 / Lint / 评分 / 建议

> **来源**: `architecture-refactor.md` §3.8.6-3.8.9
> **关联文档**: `mode-matrix.md`（模式权限）、`langgraph-graph.md`（相关节点）
> 改对抗逻辑或阈值时，需同步检查 langgraph-graph.md 中的 suggestion/change_review 节点。

## 变更计划（ChangePlan）——改前预览，按风险分级审核

> 解决：AI 改了之后用户才发现改得不对。用户应该在**改之前**就知道 AI 打算改什么、影响范围、风险等级。
> 但每次改都让用户点批准太烦了，按风险等级决定审批方式：

| ChangeScore 等级 | 审批方式 | 用户体验 |
|-----------------|---------|---------|
| **TRIVIAL** | 自动执行 | 改空格/注释，用户不需要知道 |
| **LOW** | 自动执行 + 后台记录 | 一行变量改名，事后能在历史里看到 |
| **MEDIUM** | 非阻塞通知栏提示 | 导航栏闪一下"改了 2 个文件"，用户可点开看，不点也不影响继续聊 |
| **HIGH** | 弹审批卡，阻塞 | 改了敏感函数、删文件，必须用户点头 |
| **CRITICAL** | 弹审批卡 + 标红警告 | 改了安全策略、影响整个项目 |

**触发方式**：AI 在 `chat_node` 中生成修改方案后，计算 ChangeScore，根据等级决定是自动执行还是等用户批准。

```
chat_node → CHANGE_SCORE 评估
  ├── TRIVIAL/LOW → 直接执行，后台记录
  ├── MEDIUM → 执行 + 非阻塞通知（用户不点不影响）
  └── HIGH/CRITICAL → CHANGE_PLAN（展示结构化变更）→ 用户批准/驳回 → 执行已批准的变更
  → LINT → 后续流程
```

**SSE 事件结构**（数据和原来一样，只是改为改前输出，字段名改 plan_id）：

**SSE 事件结构**（完整字段）：
```python
{
    "type": "change_review",
    "id": "cr_3",                     # 本轮变更审查 ID
    "turn_id": 3,                     # 关联的对话轮次
    "files": [
        {
            "path": "src/auth.py",
            "changes": [
                {
                    "id": "c1",
                    "type": "add_function",    # add_function / modify_function / delete_function / add_line / modify_line
                    "symbol": "login_user",    # 涉及的具体函数/变量名
                    "summary": "新增 login_user 函数，处理 JWT 登录",
                    "diff_excerpt": "+def login_user():\n+    return jwt.encode(...)",
                    "reason": "用户登录功能需要 JWT 鉴权，当前代码没有鉴权逻辑",
                    "dependencies": ["c3"],     # 依赖的其他变更 ID
                    "risk": "low"               # low / medium / high（AI 自评）
                },
                {
                    "id": "c2",
                    "type": "modify_function",
                    "symbol": "validate_token",
                    "summary": "修改 validate_token 增加过期检查",
                    "diff_excerpt": "-    return True\n+    return expires_at > now()",
                    "reason": "原有校验缺少过期时间判断，存在安全漏洞",
                    "dependencies": [],
                    "risk": "medium"
                }
            ]
        },
        {
            "path": "src/config.py",
            "changes": [
                {
                    "id": "c3",
                    "type": "add_variable",
                    "symbol": "JWT_SECRET",
                    "summary": "新增 JWT_SECRET 配置项",
                    "reason": "login_user 依赖 JWT_SECRET 作为签名密钥",
                    "dependencies": [],
                    "risk": "low"
                }
            ]
        }
    ],
    "estimated_impact": "涉及 2 个文件，3 处变更，影响 login 和 config 模块"
}
```

**前端 ChangeReviewCard 组件渲染**：
```
┌─────────────────────────────────────────────────────┐
│  第 3 轮变更审查                                        │
│  涉及 2 个文件 · 3 处变更                               │
│                                                       │
│  ┌─ src/auth.py ───────────────────────────────────┐  │
│  │                                                 │  │
│  │  ☑ 新增函数 login_user                        │  │
│  │     └ 原因: 用户登录需要 JWT 鉴权              │  │
│  │     └ 依赖: JWT_SECRET 配置项                  │  │
│  │     └ 风险: 🟢 低                              │  │
│  │     ┌─────────────────────────────────────┐    │  │
│  │     │ +def login_user():                  │    │  │
│  │     │ +    return jwt.encode(...)         │    │  │
│  │     └─────────────────────────────────────┘    │  │
│  │                                     [批准] [驳回]│  │
│  │                                                 │  │
│  │  ☑ 修改函数 validate_token                    │  │
│  │     └ 原因: 缺少过期时间判断                   │  │
│  │     └ 风险: 🟡 中                              │  │
│  │                                     [批准] [驳回]│  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  ┌─ src/config.py ─────────────────────────────────┐  │
│  │  ☑ 新增变量 JWT_SECRET                          │  │
│  │                                     [批准] [驳回]│  │
│  └─────────────────────────────────────────────────┘  │
│                                                [全部批准] │
└─────────────────────────────────────────────────────┘
```

**驳回处理**：被驳回的变更标记到 AgentState.rejected_changes，AI 分析原因后提出替代方案。

**驳回的处理逻辑（区别于简单删代码）**：

当用户驳回某处变更（如 c1: login_user），AI 不能直接删除新增代码，因为 c1 依赖 c3（JWT_SECRET），c3 可能还被其他地方引用。

```
用户驳回 c1 (login_user)
      ↓
后端将 c1 标记为 rejected
      ↓
AI 重新审视：
  1. 检查被驳回变更的依赖树
     c1 依赖 c3 → 如果用户也驳回了 c3，两者一起回滚
     c1 依赖 c3 → 如果用户批准了 c3，保留 c3（避免影响其他代码）
  2. 分析驳回原因
     - 用户直接给了理由（如"不应该用 JWT，用 session"）
     - 或用户没给理由 → AI 推测原因
  3. 提出替代方案
     - "不用 JWT，改用 Session 鉴权，需要修改 validate_token"
     - "login_user 暂时保留，等用户确认后再启用"
  4. 执行替代方案（新的子任务迭代）
```

**工具接口**：

```python
class ToolChangeReview:
    """AI 调用此工具生成变更审查数据"""

    def __call__(self, git_diff_output: str, turn_id: int) -> dict:
        """
        输入: git diff 的完整输出
        输出: 结构化的变更审查数据（每处改动 + 原因 + 依赖关系）

        AI 内部工作流程:
        1. 解析 git diff → 识别每个文件的每处改动
        2. 对每处改动添加智能分析（变更类型、涉及符号、变更原因、风险等级）
        3. 分析变更间的依赖关系（函数 A 依赖变量 B）
        4. 返回结构化的 change_review 数据
        """
        return {
            "type": "change_review",
            "files": [ ... ]  # 结构化变更数据
        }
```

**驳回后的 AI 重新审视流程**：

```
原始: AI 改完了 3 个文件
  ↓
输出 change_review 卡片
  ↓
用户: 批准 c2, c3，驳回 c1
  ↓
AI 收到驳回信息：
  ├─ c1 (login_user) rejected
  ├─ c1 依赖 c3 → c3 已批准，保留 c3
  └─ 替换方案："不用 login_user 函数，直接在路由层处理 JWT"
  ↓
AI 执行替换方案 → 输出新的 change_review（只含 c1 的替代方案）
  ↓
用户批准 → 进入下一步（REVIEW / TEST）
```

**在架构中的位置**：

```
Execute Mode 上下文:
  子链: [快速澄清 | 执行(ToolNode) | 变更审查 | 自检 | 回滚 | 重构评估]
                                    ↑
                        新增节点：AI 执行完毕后自动触发

触发方式：
  1. AI 每轮执行完所有工具调用后自动调用 ToolChangeReview
  2. AI 也可以选择跳过（如果只改了 1 行注释），由 AI 自行判断
  3. 用户可以主动要求："帮我展示刚才改了什么"

与现有审批系统的关系：
  - 现有审批（Casbin）：在"执行前"拦截（如删除文件、git push --force）
  - 变更审查：在"执行后"展示，让用户逐项确认
  - 两者不冲突：高风险操作先审批再执行，执行完后再审查
```

**不认可变更的拒绝机制**：

```
用户点击 [驳回] 时，可附带理由：
  - "这个改法不对，应该用装饰器"
  - "不需要这个函数"
  - 或者不填理由（AI 会自行分析为何被驳回）

后端接收到驳回后：
  1. 将驳回变更的 id 标记到 AgentState.rejected_changes 中
  2. LangGraph 条件路由自动导向 review_node（而非结束）
  3. AI 在 review_node 中：
     - 看到 rejected_changes 列表
     - 分析每项被拒的原因
     - 提出替代方案
     - 调用 execute_node 执行替代
     - 生成新的 change_review
```

## Linter

| 层面 | 检查内容 | 谁执行 | 何时执行 |
|------|---------|--------|---------|
| **语法格式层** | 缩进、命名、导入、类型标注 | Linter（此节）— 自动、静默、可 auto-fix | 每次改完代码后立即执行 |
| **代码质量层** | API 设计、实现优雅度、注释清晰度 | AI 对抗审查（SuggestionCard）— 用户选择是否执行 | 用户从对抗建议中选择后 |

推荐的 linter：**Ruff**（Python 项目，Rust 编写，支持 --fix 自动修复）。

```
EXECUTE（改代码）→ LINT（自动运行 ruff）
  ├── 全部通过 → 直接输出 change_review
  ├── 可自动修复 → auto-fix → 重新 lint → 输出 change_review
  └── 不可修复 → 标记到 change_review 的 lint_issues 字段
```

## 变更评分（ChangeScore）

```python
class ChangeLevel(IntEnum):
    TRIVIAL = 0  # 单行改动
    LOW = 1      # 单文件单函数
    MEDIUM = 2   # 单文件多函数或小范围跨文件
    HIGH = 3     # 多文件跨模块
    CRITICAL = 4 # 系统架构性改动

@dataclass
class ChangeScore:
    level: ChangeLevel
    files_changed: int = 0
    modules_affected: int = 0
    functions_added: int = 0
    functions_modified: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    suggested_actions: list[str] = field(default_factory=list)
    suggest_reason: str = ""

    @classmethod
    def from_git_diff(cls, diff_output: str) -> "ChangeScore": ...
```

> **v1 范围**：仅统计文件数、行数、模块数（基于 git diff 文件路径推断）。`functions_added`/`functions_modified` 字段保留但不参与评分，v2 再通过函数识别增强。
>
> **依赖分析**：`change_review` 中的 `dependencies` 字段由 AI 在 change_review 节点中智能判断，不做自动 AST 解析。v2 再考虑精确依赖分析。

## 对抗建议（SuggestionCard）

**核心原则**：AI 建议，用户决定。不是自动执行，是输出建议卡片让用户选择。

```
Blue（Developer）: 负责写代码、改代码
Red（Reviewer/Tester/Architect）: 负责挑错、测试、重构建议

介入方式：蓝方改动完成 → AI 计算评分 → 建议卡片 → 用户选择是否执行
```

**建议卡片 SSE 事件**（注意：SSE 事件类型名为 `suggestion`，保持在 api-reference.md 中定义的统一命名）：
```python
{
    "type": "suggestion",
    "id": "as_3", "turn_id": 3,
    "summary": "你改了 5 个文件(2个模块)，变更幅度较大",
    "level": "HIGH",
    "suggested_actions": [
        {"id": "full_review", "title": "逐文件代码质量审查", "desc": "...", "estimated_time": "约 2 轮对话"},
        {"id": "unit_test", "title": "运行单元测试", "desc": "...", "estimated_time": "约 30 秒"},
        {"id": "integration_test", "title": "运行集成测试", "desc": "..."},
        {"id": "architect_review", "title": "架构评估", "desc": "..."}
    ],
    "ai_reason": "新增功能模块涉及多个文件交叉引用，建议先做架构评估"
}
```

**用户交互**：
1. 用户调整勾选 → [执行选中项] → AI 按勾选执行
2. 用户什么都不做 → 卡片持续显示，不自动执行
3. 用户点 [跳过] → 直接进入下一步

## 测试集成

开发完成 → Agent 进入 REVIEWING 状态 → MultiRoleManager 切换 tester 身份 → 运行测试（tool_bash("pytest")）→ 全部通过则继续，有失败则修复后重新审查。

## 与 MultiRoleManager 的联动

对抗不是让模型"自己打自己"，而是切换 system prompt 改变视角：

```
用户选了"逐文件对抗审查"后：
  1. MultiRoleManager 将 persona 从 "developer" 切换到 "reviewer"
  2. AI 以 reviewer(对抗) 身份审阅
  3. 审查结果输出到对话
  4. 完成后 MultiRoleManager 切回 "developer"
  5. 回到对抗建议卡片 → 用户决定是否继续下一项
```

### handle_adversarial_decision

```python
def handle_adversarial_decision(state: AgentState, user_choice: dict) -> dict:
    """用户勾选了建议卡中的项，执行对应对抗动作"""
    selected = user_choice.get("selected", [])
    actions = {
        "full_review": "reviewer_adversarial",
        "unit_test": "run_tests",
        "integration_test": "run_integration_tests",
        "architect_review": "architect_assessment",
        "architect_report": "architect_report_to_user",
        "skip": "done",
    }
    next_node = actions.get(selected[0], "done")
    return {"next": next_node, "phase": next_node}
```

### IConversationStore 与 LangGraph Checkpointer 的职责区分

| 维度 | IConversationStore | LangGraph Checkpointer |
|------|------------|----------------------|
| 存储内容 | 对话消息列表 + 成本记录 + 用户偏好 | LangGraph 状态快照（含审批挂起点） |
| 用途 | **跨会话**：历史记录、关掉再开、会话列表 | **单会话内**：中断恢复、回滚到上一轮 |
| 持久化 | 长期（SQLite/PostgreSQL） | 短期（SqliteSaver 持久化到 langgraph.db） |
| 恢复方式 | 前端 `useChat({ initialMessages })` 加载 | LangGraph 从 Checkpointer 恢复状态 |

### 全部通过 SuggestionCard 触发

不硬编码管线。架构只提供"切换能力"和"情报"（ChangeScore、变更审查数据），不做流程控制。用户全程决定是否执行每项审查：

| 动作 | 触发 persona | 触发方式 |
|------|-------------|---------|
| 代码审查 | reviewer | AI 建议 → 用户确认 |
| 运行测试 | tester | AI 建议 → 用户确认 |
| 架构评估 | architect | AI 建议 → 用户确认 |
| 完成后更新文档 | documenter | AI 建议 → 用户确认 |

## Linter 完整实现（ToolLint）

语法格式层自动修复（Ruff），不可自动修复的问题标记到 change_review 中。

| 层面 | 检查内容 | 谁执行 | 何时执行 |
|------|---------|--------|---------|
| **语法格式层** | 缩进、命名规范、导入顺序、未使用变量 | **Linter** — 自动、静默、可 auto-fix | 改完代码后立即执行 |
| **代码质量层** | API 设计、实现优雅度、注释清晰度 | **AI 对抗审查** — 用户选择是否执行 | 用户从对抗建议中选择后 |

```python
# infrastructure/tools/tool_lint.py
import subprocess, json

class ToolLint:
    """AI 写文件后自动调用，静默修复 lint 问题"""

    def __call__(self, changed_files: list[str] | None = None) -> dict:
        results = {"auto_fixed": 0, "remaining": []}

        # Step 1: 自动修复
        fix_result = subprocess.run(
            ["ruff", "check", "--fix", *changed_files] if changed_files
            else ["ruff", "check", "--fix", "."],
            capture_output=True, text=True
        )
        results["auto_fixed"] = self._parse_fixed_count(fix_result.stdout)

        # Step 2: 获取剩余问题
        check_result = subprocess.run(
            ["ruff", "check", "--output-format", "json", *changed_files]
            if changed_files else ["ruff", "check", "--output-format", "json", "."],
            capture_output=True, text=True
        )
        if check_result.stdout:
            results["remaining"] = json.loads(check_result.stdout)
        return results

    def _parse_fixed_count(self, output: str) -> int:
        import re
        match = re.search(r"(\d+) fixed", output)
        return int(match.group(1)) if match else 0
```

**执行流程**：

```
执行前 → [审批] → 执行 → [LINT 自动修复] → [变更审查] → [测试] → 完成
```

lint 结果附加到 change_review 事件的 `lint_issues` 字段。

## generate_suggestion（对抗建议生成引擎）

```python
def generate_suggestion(score: ChangeScore) -> dict:
    """根据评分生成对抗建议（不执行，只建议）"""
    suggestions = []

    if score.level >= ChangeLevel.MEDIUM:
        suggestions.append({
            "id": "full_review",
            "title": "逐文件代码质量审查",
            "desc": "reviewer 角色审查 API 一致性、实现优雅度",
            "estimated_time": "约 2 轮对话",
            "default_selected": score.level >= ChangeLevel.HIGH
        })
        suggestions.append({
            "id": "unit_test",
            "title": "运行单元测试",
            "desc": "受影响模块的单元测试",
            "estimated_time": "约 30 秒",
            "default_selected": True
        })

    if score.level >= ChangeLevel.HIGH:
        suggestions.append({
            "id": "integration_test", "title": "运行集成测试",
            "desc": "跨模块集成测试", "estimated_time": "约 2 分钟",
            "default_selected": False
        })
        suggestions.append({
            "id": "architect_review", "title": "架构评估",
            "desc": "评估变更对整体架构的影响", "estimated_time": "约 3 轮对话",
            "default_selected": False
        })

    if score.level >= ChangeLevel.CRITICAL:
        suggestions.append({
            "id": "architect_report", "title": "架构影响报告",
            "desc": "向用户输出完整的架构影响分析报告",
            "estimated_time": "阅读约 1 分钟", "default_selected": True
        })

    return {
        "summary": f"你改了 {score.files_changed} 个文件({score.modules_affected}个模块)",
        "level": score.level.name,
        "suggestions": suggestions,
        "ai_reason": _generate_reason(score)
    }
```

## suggestion_node（在 LangGraph 中的实现）

```python
def suggestion_node(state: AgentState) -> dict:
    """根据 ChangeScore 生成对抗建议卡片"""
    score = state.get("change_score")
    if score is None:
        return {"messages": []}

    suggestion = generate_suggestion(score)
    if not suggestion["suggestions"]:
        return {"next": "done", "messages": []}

    return {
        "adversarial_suggestion": suggestion,
        "phase": "awaiting_adversarial_decision",
        "messages": []
    }

def handle_adversarial_decision(state: AgentState, user_choice: dict) -> dict:
    """用户勾选了建议卡中的项，执行对应对抗动作"""
    selected = user_choice.get("selected", [])
    actions = {
        "full_review": "reviewer_adversarial",
        "unit_test": "run_tests",
        "integration_test": "run_integration_tests",
        "architect_review": "architect_assessment",
        "architect_report": "architect_report_to_user",
        "skip": "done",
    }
    next_node = actions.get(selected[0], "done")
    return {"next": next_node, "phase": next_node}
```

## 责任链模式重构建议

当前 Lint→ChangeReview→Suggestion 的固定边是 hard-coded 在 LangGraph 的图定义中的。未来若要新增审核环节（安全扫描、性能分析、版权检查），需修改 graph.py 的路由——这违反开闭原则。

**责任链模式**让每个审核环节成为一个独立的 Handler，环节之间通过链式调用松耦合：

```python
from abc import ABC, abstractmethod

class ReviewHandler(ABC):
    """审核责任链节点"""
    def __init__(self):
        self._next = None

    def set_next(self, handler: "ReviewHandler") -> "ReviewHandler":
        self._next = handler
        return handler  # 支持链式调用

    @abstractmethod
    async def handle(self, ctx: ReviewContext) -> ReviewResult | None:
        """处理请求，返回 None 表示交给下一个"""
        ...

@dataclass
class ReviewContext:
    file_path: str
    diff: str
    turn_id: int

@dataclass
class ReviewResult:
    blocked: bool = False
    reason: str = ""
    issues: list = field(default_factory=list)

class LintHandler(ReviewHandler):
    """语法格式检查（Ruff）"""
    async def handle(self, ctx) -> ReviewResult | None:
        issues = await run_ruff(ctx.file_path)
        if not issues:
            return None  # 没发现问题，交给下一个
        return ReviewResult(issues=issues)

class SecurityHandler(ReviewHandler):
    """安全风险扫描"""
    async def handle(self, ctx) -> ReviewResult | None:
        if "rm -rf" in ctx.diff or "DROP TABLE" in ctx.diff:
            return ReviewResult(blocked=True, reason="检测到危险操作")
        if "eval(" in ctx.diff or "exec(" in ctx.diff:
            return ReviewResult(issues=[{"type": "security", "detail": "动态执行代码"}])
        return None  # 安全，交给下一个

class StyleHandler(ReviewHandler):
    """代码风格一致性检查"""
    async def handle(self, ctx) -> ReviewResult | None:
        # ... 检查命名规范、缩进一致性等 ...
        return None

# 使用
chain = LintHandler()
chain.set_next(SecurityHandler()).set_next(StyleHandler())

result = await chain.handle(ReviewContext(file_path, diff))
# result 为 None 表示全部通过，否则取最后一个有返回的 Handler 的结果
```

**效果**：加一个新审核环节 = 写一个新 Handler 类 + 一行 `.set_next(NewHandler())`，不用改 graph.py 的路由逻辑。

> **关联文档**: `tools.md`（ToolLint）、`langgraph-graph.md`（节点路由）

---

## 建议反馈记录（Minimal）

> **原则**：只记录，不分析。AI 给建议 → 用户点 ✅/❌ → 写 JSONL。为未来自动调优留数据，当前完全不分析。

### 1. `suggest_node` 输出携带 `suggestion_id`

每张 SuggestionCard 生成一个 UUID，写入 SSE 事件：

```python
import uuid

def suggest_node(state: AgentState) -> dict:
    score = state.get("change_score")
    if score is None:
        return {"messages": []}

    suggestion = generate_suggestion(score)
    if not suggestion["suggestions"]:
        return {"next": "done", "messages": []}

    suggestion_id = str(uuid.uuid4())

    # 不阻塞：Store 写入由 chat_node 统一调度，这里只传 ID
    return {
        "adversarial_suggestion": {**suggestion, "suggestion_id": suggestion_id},
        "phase": "awaiting_adversarial_decision",
        "messages": []
    }
```

SSE 事件中增加 `suggestion_id` 字段：

```python
{
    "type": "suggestion",
    "suggestion_id": "sg_a1b2c3",
    "summary": "你改了 3 个文件(2 个模块)",
    "level": "HIGH",
    "suggestions": [ ... ]
}
```

### 2. 反馈 API（走 ConversationStore）

```python
# backend/routes/feedback.py
from di.container import Container

@app.post("/api/feedback/suggestion")
async def submit_feedback(suggestion_id: str, adopted: bool):
    store = Container.get("conversation_store")
    await store.update_suggestion_feedback(suggestion_id, adopted)
    return {"ok": True}
```

### 3. 前端 SuggestionCard 加 ✅/❌ 按钮

在 `SuggestionCard.vue` 底部加两个按钮，调 `POST /api/feedback/suggestion`：

```
┌─────────────────────────────────────────────────┐
│  你改了 3 个文件 (2 个模块)  [HIGH]              │
│                                                 │
│  ☑ 逐文件代码质量审查    ⏱ 约 2 轮对话           │
│  ☑ 运行单元测试          ⏱ 约 30 秒              │
│  ☐ 运行集成测试          ⏱ 约 2 分钟              │
│  ☐ 架构评估              ⏱ 约 3 轮对话            │
│                                                 │
│           [✅ 采纳建议] [❌ 不需提醒]             │
└─────────────────────────────────────────────────┘
```

> **注意**：✅/❌ 仅用于记录反馈，不影响当前对话流程。用户勾选哪些项执行是通过 `handle_adversarial_decision` 决定的，两套逻辑独立。

### 4. 按 rule_name 统计采纳率（数据来自 ConversationStore）

等 SaaS 用户量上来了，从 ConversationStore 里查 suggestion 反馈数据：

```python
records = await store.search("", session_id=None)
# 过滤出有 adopted 字段的轮次，按 rule_name 分组统计
```

> **关联文档**: `api-reference.md`（SSE 事件格式 + `/api/feedback/suggestion` 端点）、`backend-modules.md`（文件夹树）
