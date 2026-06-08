# 对抗体系：审查 / Lint / 评分 / 建议

> **来源**: `architecture-refactor.md` §3.8.6-3.8.9
> **关联文档**: `mode-matrix.md`（模式权限）、`langgraph-graph.md`（相关节点）
> 改对抗逻辑或阈值时，需同步检查 langgraph-graph.md 中的 suggestion/change_review 节点。

## 变更审查（ChangeReview）

> 解决：AI 改完一批文件后用户只能「全盘接受」或「全盘拒绝」的问题。
> 实际上用户可能：认可文件 A 的改动但不认可文件 B；认可某个函数但不认可同文件中另一处修改；对某个改动有疑虑希望 AI 解释后决定。

**触发方式**：系统在 `execute_node` 执行完毕后自动调用（作为 ToolNode 的后续节点）。AI 在每次文件变更工具调用后，LangGraph 条件边自动导向 `change_review` 节点，无需 AI 手动触发。

```
EXECUTE（改代码）→ LINT（静默修复）→ CHANGE_REVIEW（系统自动调用）→ 用户逐项确认/驳回
  → 被驳回的变更 → AI 分析原因 → 提出替代方案 → 重新审查
```

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

**建议卡片 SSE 事件**：
```python
{
    "type": "adversarial_suggestion",
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

开发完成 → Agent 进入 REVIEWING 状态 → PromptManager 切换 tester 身份 → 运行测试（tool_bash("pytest")）→ 全部通过则继续，有失败则修复后重新审查。

## 与 PromptManager 的联动

对抗不是让模型"自己打自己"，而是切换 system prompt 改变视角：

```
用户选了"逐文件对抗审查"后：
  1. PromptManager 将 persona 从 "developer" 切换到 "reviewer"
  2. AI 以 reviewer(对抗) 身份审阅
  3. 审查结果输出到对话
  4. 完成后 PromptManager 切回 "developer"
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

### IRepository 与 LangGraph Checkpointer 的职责区分

| 维度 | IRepository | LangGraph Checkpointer |
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
