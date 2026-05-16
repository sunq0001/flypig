# 友商参考 — Peer Reference & Competitive Analysis

> 对标项目：**Aider** (Python, 45K ⭐) + **DeepSeek TUI** (Rust, v0.8.38)
>
> 目的：了解行业头部项目的架构设计，提炼可借鉴到 FlyPig 的模式

---

## 1. Aider (Python CLI Agent)

| 项目 | 值 |
|------|-----|
| 仓库 | Aider-AI/aider |
| 语言 | Python 80% |
| Stars | ~45K |
| 定位 | 终端 AI 结对编程工具 |
| 安装 | `pip install aider-chat` |

### 1.1 架构核心

```
aider/main.py (入口)
    │
    ├─ Coder.create() 工厂 — 按 edit_format 创建对应 Coder
    │   ├── EditBlockCoder     ("diff")       — SEARCH/REPLACE 块
    │   ├── UnifiedDiffCoder   ("udiff")      — unified diff
    │   ├── WholeFileCoder     ("whole")      — 整文件替换
    │   ├── PatchCoder         ("patch")      — git patch 格式
    │   ├── ArchitectCoder     ("architect")  — 双模型分层
    │   └── AskCoder           ("ask")        — 仅对话
    │
    ├─ RepoMap (代码库地图)
    │   └─ tree-sitter 标签 → PageRank 排序 → token 预算截断
    │
    ├─ GitRepo (版本控制)
    │   └─ 自动 commit + 安全 undo
    │
    └─ InputOutput (IO 抽象层)
        └─ prompt_toolkit 封装
```

### 1.2 最值得借鉴的设计

#### ① Edit Format 插件架构（Template Method）
Aider 最核心的设计。基类定义流程骨架，子类通过重写 `get_edits()` / `apply_edits()` 实现不同编辑格式：

```python
# base_coder.py (模板方法)
def apply_updates(self):
    edits = self.get_edits()                # 子类：从 LLM 回复解析编辑
    edits = self.apply_edits_dry_run(edits)  # 预演验证
    edits = self.prepare_to_edit(edits)      # Git 备份
    self.apply_edits(edits)                  # 子类：写入文件
```

**价值**：LLM 只输出"变化部分"（SEARCH/REPLACE block），比全文件替换省 50-80% token。

#### ② 柔性匹配引擎 (`search_replace.py`)
LLM 输出的代码块和实际文件往往有细微差异（缩进、空白行、省略号）。Aider 实现了 5 层容错：

| 层级 | 策略 | 方法 |
|------|------|------|
| 1 | 精确匹配 | `perfect_replace()` — 逐行完全匹配 |
| 2 | 前导空格容错 | `replace_part_with_missing_leading_whitespace()` |
| 3 | 省略空白行 | 跳过多余 blank line |
| 4 | `...` 省略号 | `try_dotdotdots()` |
| 5 | 编辑距离模糊 | `replace_closest_edit_distance()` (相似度 > 0.8) |

#### ③ Git 自动 commit + 安全 undo
每次 AI 编辑后自动 commit，commit message 由 LLM 生成。`/undo` 只撤销 AI 创建的 commit：

```
apply_updates() → auto_commit() → git add + git commit
                                  → commit hash 记录到 aider_commit_hashes
                                  → /undo 只查有 hash 记录的 commit
```

#### ④ RepoMap 代码库地图
tree-sitter 解析 → def/ref 标签 → PageRank 排序 → 按 token 预算截断渲染

#### ⑤ IO 层依赖注入
```python
class Coder:
    def __init__(self, main_model, io, repo, repo_map):
        self.io = io          # 所有交互通过 io 接口
```

### 1.3 FlyPig 已有/可借鉴对比

| 特性 | Aider | FlyPig | 可否借鉴 |
|------|-------|--------|---------|
| Edit Format (SEARCH/REPLACE) | ✅ 5 层容错 | ❌ 只有全文件 write | **P0 - 强烈推荐** |
| Git 自动 commit + undo | ✅ | ❌ | **P0 - 强烈推荐** |
| RepoMap 代码地图 | ✅ PageRank | ❌ 无 | P2 |
| IO 抽象层 | ✅ 注入式 | ❌ 直接操作 UI | **P1 - 推荐** |
| 双模型架构 | ✅ ArchitectCoder | ❌ | P3 |
| TUI 界面 | ❌ 纯 CLI | ✅ Textual TUI | FlyPig 领先 |
| Tool Calling | ✅ Function Calling | ✅ function_call | 持平 |
| 成本追踪 | ❌ | ✅ CostTracker | FlyPig 领先 |

---

## 2. DeepSeek TUI (Rust TUI Agent)

| 项目 | 值 |
|------|-----|
| 仓库 | Hmbown/DeepSeek-TUI |
| 语言 | Rust (edition 2024) |
| 版本 | v0.8.38 |
| 代码量 | ~120K-150K 行 Rust |
| 定位 | DeepSeek 模型的 TUI 工具 |

### 2.1 架构核心

```
crates/tui (主运行时)        crates/core (推理引擎)       crates/tools (工具注册表)
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│  ratatui 界面         │   │  engine.rs            │   │  registry.rs          │
│  tui/                 │   │  turn_loop.rs          │   │  file.rs               │
│  app.rs  (状态机)     │   │  session.rs            │   │  shell.rs              │
│  ui.rs   (~10K行)    │   │  ops.rs / events.rs    │   │  git.rs                │
│  Layout: 多面板布局   │   │  (Op/Event 消息驱动)   │   │  subagent/             │
└──────────┬───────────┘   └──────────┬──────────────┘   └──────────┬──────────┘
           │                          │                              │
           └──────────────────────────┼──────────────────────────────┘
                                      │
                           runtime_threads.rs (回合持久化)
                           runtime_api.rs (HTTP/SSE API)
                                mcp.rs (MCP 协议)
                           ┌─────────────────────┐
                           │ config.rs (~5500行)  │
                           │ state/ (SQLite)      │
                           │ secrets/ (密钥环)     │
                           └─────────────────────┘
```

### 2.2 最值得借鉴的设计

#### ① 事件驱动架构 (Op/Event 通道)
DeepSeek TUI 的事件驱动架构非常优雅：

```
用户操作 → App (状态机) → Op (操作命令) → Engine 处理 → Event (结果事件) → UI 更新
                          │                    │
                     mpsc channel          SSE/WebSocket
```

所有交互通过消息队列（mpsc channel）传递，UI 和 Engine 完全解耦。UI 只发 Op 收 Event，不直接调用 Engine。

#### ② 多层次会话管理系统

| 层级 | 文件 | 作用 |
|------|------|------|
| Session | `core/session.rs` | 持久化会话（SQLite + JSON） |
| Turn | `core/turn.rs` | 单次问答回合（推理、摘要） |
| TurnLoop | `core/engine/turn_loop.rs` | 循环管理（重试、回退） |

会话分层设计，支持：
- 会话恢复（保存/加载）
- 消息截断 + 摘要压缩
- 并行运行多个独立会话

#### ③ 丰富的 TUI 布局
ratatui 实现的复杂多面板布局：

```
┌─ 标题栏 ────────────────────────────────────┐
│ [会话标题] [模型名] [Token消耗]              │
├────────────┬────────────────────┬────────────┤
│ 文件树     │ 代码/文件内容     │ 对话面板   │
│ (展开/收起) │                    │ (彩色高亮) │
│            │                    ├────────────┤
│            │                    │ 工具输出   │
│            │                    │ (折叠式)   │
├────────────┴────────────────────┴────────────┤
│ 输入栏 [多行输入 / 命令 / 自动补全]          │
│ 状态栏 [运行中/等待/错误] [快捷键帮助]      │
└──────────────────────────────────────────────┘
```

注意：DeepSeek TUI 是用 **ratatui** 实现的即时渲染（immediate mode），而 FlyPig 用 **Textual**（retained mode / widget tree）。Textual 在 Widget 复用和布局灵活性上更强。

#### ④ 工具注册表 (Tool Registry)
```rust
// tools/registry.rs
pub struct ToolRegistry {
    tools: HashMap<String, Box<dyn Tool>>,
}

pub trait Tool {
    fn name(&self) -> &str;
    fn description(&self) -> &str;
    fn schema(&self) -> ToolSchema;       // JSON Schema for LLM
    fn execute(&self, args: &str) -> Result<String>;
}
```

每个工具是一个独立 trait 实现，通过注册表统一管理 schema 和调用。

#### ⑤ MCP 协议支持
内置 MCP (Model Context Protocol) 客户端，支持连接外部 MCP Server 扩展能力。

#### ⑥ 灵活的配置文件
`config.rs` (~5500 行) 支持多 Provider、多 Profile、多环境变量源，配置即代码。

#### ⑦ Skill / Hook 扩展系统
- **Skills**：预定义行为/工作流
- **Hooks**：事件回调（类似 FlyPig 的 hooks.py）
- **SubAgent**：子 Agent 并行执行

### 2.3 FlyPig 可借鉴点

| 特性 | DeepSeek TUI | FlyPig | 可否借鉴 |
|------|-------------|--------|---------|
| 事件驱动架构 | ✅ Op/Event 通道 | ❌ 直接调用 | **P2** |
| 会话分层管理 | ✅ Session/Turn/TurnLoop | ❌ 简单消息列表 | **P1** |
| 工具注册表 | ✅ ToolRegistry trait | ✅ get_tools_schema() | 持平 |
| MCP 支持 | ✅ | ❌ | P3 |
| 配置系统 | ✅ 多Provider/多Profile | ✅ config.yaml | 持平 |
| Skill 系统 | ✅ | ❌ | P2 |
| SubAgent | ✅ | ❌ | P3 |
| TUI 布局 | ratatui 多面板 | Textual 三栏四区 | FlyPig 更强 |

---

## 3. 综合对比雷达图

```
                 Aider    DeepSeek TUI    FlyPig
                 ─────    ────────────    ──────
Edit Format      █████    ██░░░          ██░░░
Git 集成         █████    ███░░          ██░░░
TUI 界面         ██░░░    ████░          █████
会话管理         ████░    █████          ███░░
工具调用         ████░    █████          ████░
代码理解         █████    ███░░          ███░░
扩展性           ████░    █████          ██░░░
事件驱动         ██░░░    █████          ██░░░
```

---

## 4. 推荐优先借鉴到 FlyPig 的 Feature

基于对两个头部项目的分析，按 FlyPig 当前阶段排序：

### P0（立即做，收益最大）

| Feature | 来源 | 预计工作量 | 收益 |
|---------|------|-----------|------|
| **Edit Format 柔性匹配** | Aider | 3-5 天 | token 节省 50-80%，编辑更可靠 |
| **Git 自动 commit + undo** | Aider | 2-3 天 | 用户安全感、可回退 |

### P1（接下来做，架构改善）

| Feature | 来源 | 预计工作量 | 收益 |
|---------|------|-----------|------|
| **IO 抽象层** | Aider | 2 天 | 解耦 UI，方便自动化测试 |
| **会话分层管理** | DeepSeek TUI | 3-4 天 | 会话持久化、历史恢复 |

### P2（中期做，体验提升）

| Feature | 来源 | 预计工作量 | 收益 |
|---------|------|-----------|------|
| **轻量 RepoMap** | Aider | 5-7 天 | LLM 更好理解代码上下文 |
| **工具注册表** | DeepSeek TUI | 1-2 天 | 插件化的 Schema 管理 |
| **事件驱动重构** | DeepSeek TUI | 5-7 天 | UI 不阻塞，响应更快 |

### P3（长期愿景）

| Feature | 来源 | 预计工作量 | 收益 |
|---------|------|-----------|------|
| 双模型 Architect | Aider | 5-7 天 | 大文件编辑更聪明 |
| MCP 协议支持 | DeepSeek TUI | 5-7 天 | 扩展生态系统 |
| Skill 系统 | DeepSeek TUI | 3-5 天 | 可复用的工作流 |
| SubAgent | DeepSeek TUI | 5-7 天 | 并行执行 |

---

## 5. FlyPig 相对优势（保持并强化）

一些方面 FlyPig 已经做得更好，**不要因为对手而放弃**：

| 方面 | FlyPig 优势 | 说明 |
|------|------------|------|
| **TUI 界面** | Textual 比 ratatui 更灵活 | 三栏四区域 + 拖拽，用户已认可 |
| **成本追踪** | CostTracker 完整 | Aider 和 DeepSeek TUI 都没有 |
| **Windows 适配** | 完整 Windows 命令转换 | Aider 仅限 Unix |
| **沙箱隔离** | Docker 沙箱（开发中） | 两个对手都没有 |
| **钩子系统** | 6 生命周期事件钩子 | 两个对手都没有 |
| **Python 生态** | pip install 即用 | Aider 也是 Python，DeepSeek TUI 需 Rust 编译 |

---

## 6. 总结

FlyPig 当前的**最短缺**的能力：
1. **编辑可靠性** — 加 Edit Format 柔性匹配 + 增量 diff
2. **版本安全感** — 加 Git 自动 commit + undo
3. **可测试性** — 加 IO 抽象层

而 FlyPig 的 TUI、成本追踪、沙箱安全已经在业内领先，**无需盲目照搬**。

> 最后更新：2026-05-16
