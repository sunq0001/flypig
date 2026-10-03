# MCP 协议集成（Capability Management）

> **关联文档**: `frontend-arch.md`（能力管理面板 UI 设计）、`tools.md`（内置工具列表）、`backend-modules.md`（后端路由）
> 涉及 MCP 服务器的配置、发现、安装流程。

---

## 命名约定

| 场景 | 命名 | 说明 |
|------|------|------|
| 前端用户界面（按钮/面板/菜单） | **能力** / Capabilities | 用户看到的名字，不暴露 MCP 术语 |
| 后端代码（Python 模块/类/函数） | **MCP** / mcp | 开发者看到的命名 |
| REST API 端点 | `/api/mcp` | API 是对前端服务的，用用户语言 |
| 配置文件 | `mcp.json` | 开发者直接操作的文件 |
| 代码目录 | `infrastructure/tools/mcp/` | 后端模块路径 |
| 前端组件目录 | `components/mcp/` | UI 组件路径 |

**核心原则**：用户看到的是"能力"，代码里的是"MCP"。

---

## 核心理念

MCP Server 是 FlyPig Agent 的能力扩展系统，类似 VS Code 的插件生态。
底层是标准 MCP 协议，前端统一以"能力"呈现给用户。

```
VS Code:    扩展 (Extensions) → 底层是 extension API
浏览器:     扩展 (Extensions) → 底层是 WebExtension API
FlyPig:     能力 (Capabilities) → 底层是 MCP 协议
```

### 能力分层

| 用户看到的 | 底层实现 | 特性 |
|-----------|---------|------|
| 内置能力（bash / 文件操作 / 搜索） | 内置 Python 工具函数 | 预装、不可卸载、可禁用 |
| 安装的能力（数据库 / 翻译 / Git 等） | MCP Server | 从商店或手动安装 |
| 自定义能力 | 手动配置的 MCP Server | 用户自己写配置 |

---

## 前端布局（参照 VS Code 扩展面板）

> 详细 UI 设计参见 `frontend-arch.md` → 能力管理面板

### Activity Bar

```
┌─────────┐
│ 📁 文件  │  ← 当前选中
│ 🧩 能力  │  ← 新增：点击切换侧边栏为能力管理面板
│ 📋 任务  │
│ 📊 统计  │
│ ⚙ 设置  │
└─────────┘
```

### 能力面板布局（左右分栏）

```
┌──────────┬────────────────────────────────────────┐
│  搜索能力  │  🗄️ 数据库能力                          │
│  │        │                                         │
│  │  ◉ 已安装 │  让 AI 连接你的数据库，执行 SQL 查询    │
│  │  ├─ 🗄️ 数据库│  v0.3.2 · 860 次调用              │
│  │  ├─ 📖 翻译 │  [◉ 启用]  [⚙ 设置]  [卸载]       │
│  │  ├─ 🔍 搜索 │                                         │
│  │  └─ 🌐 抓取 │  可用工具:                              │
│  │           │  ✓ query_db      — 执行 SQL 查询        │
│  │  🏪 商店  │  ✓ list_tables   — 列出所有表           │
│  │  ├─ 📧 邮件│  ✓ describe_table — 查看表结构         │
│  │  ├─ 📅 日历│                                         │
│  │  ├─ 🤖 自动化│ ┌─ 连接配置 ───────────────────┐       │
│  │  └─ ...  │  │ 数据库路径:  C:\data\my.db   │       │
│  │           │  │            [浏览]            │       │
│  └──────────┴──└──────────────────────────────┘─────────┘
```

### 内置能力的特殊标记

内置能力在 UI 上标记为 **"内置"**：

```
📁 文件操作能力
   内置 · 预装在 FlyPig 中 · 不可卸载
   
   ✓ read_file       — 读取文件
   ✓ write_file      — 写入文件
   ...
```

---

## 后端 API

REST 接口（注册在 `backend/routes/` 下）：

| 端点 | 方法 | 用途 |
|------|------|------|
| `GET /api/mcp` | 列出所有能力（内置 + 已安装） | 前端渲染能力列表 |
| `GET /api/mcp/:name` | 查看能力详情 | 工具列表 + 配置 + 统计 |
| `POST /api/mcp/install` | 安装新 MCP Server | Marketplace 安装 |
| `POST /api/mcp/:name/uninstall` | 卸载 MCP Server | 移除 |
| `POST /api/mcp/:name/toggle` | 启用/禁用 | 不卸载但暂停使用 |
| `GET /api/mcp/marketplace?q=xx` | 搜索 MCP Registry | 发现新能力 |
| `PUT /api/mcp/:name/config` | 更新能力配置 | 配置面板保存 |

> 内置能力不可卸载，但可禁用。

---

## 文件结构

```
后端（MCP 命名 — 开发者视角）:

infrastructure/tools/mcp/         ← MCP 协议工具子包
├── tool_mcp_loader.py            ← 启动时加载 mcp.json，连接服务器，注册到 ToolNode
├── tool_mcp_manager.py           ← MCP 自助安装（调用 mcp-auto-install）
├── tool_mcp_controller.py        ← /api/mcp/* REST 接口
├── tool_mcp_discovery.py         ← MCP Registry 搜索
└── tool_mcp_lifecycle.py         ← 启停/健康检查

mcp.json                          ← MCP 服务器配置文件（项目根目录）


前端（组件名用 Mcp 前缀，UI 显示为"能力"）:

components/mcp/                   ← MCP 管理 UI 组件
├── McpDashboard.vue              ← 左右分栏容器（主页）
├── McpList.vue                   ← 左侧列表 + 搜索 + tab
├── McpItem.vue                   ← 列表单项
├── McpDetail.vue                 ← 右侧详情
├── McpConfig.vue                 ← MCP 配置面板
└── McpMarketplace.vue            ← 商店（搜索+安装）

composables/useMcp.js             ← MCP 管理逻辑封装
```

---

## MCP 三层策略

### 第一层：基础配置（项目自带，开箱即用）

项目默认附带 `mcp.json`，预装最常用的 MCP 服务器：

```json
{
  "mcpServers": {
    "web-search": {"command": "npx", "args": ["@anthropic/mcp-server-web-search"]},
    "fetch": {"command": "npx", "args": ["@anthropic/mcp-server-fetch"]}
  }
}
```

### 第二层 + 第三层：AI 按需发现 + 自动安装

不自研注册表，使用 `mcp-auto-install`：

```
AI 遇到需要搜索网页但没装搜索能力：
  → 调用 mcp-auto-install 提供的 install_mcp_server 工具
  → 自动搜索官方 MCP Registry
  → 找到 @anthropic/mcp-server-web-search
  → 用户[批准] → 自动下载安装 + 写入 mcp.json
  → tool_mcp_loader 热加载 → 注册到 ToolNode
  → AI 立即可用
```

> **安全**：安装时弹审批卡片，用户批准后才执行安装。

---

## LLM 侧不受影响

MCP 管理是**用户界面 + 后端管理**层的变化。LLM 对话流程（LangGraph ToolNode）仍然通过 `tool_mcp_loader.py` 加载所有已启用 MCP Server 的 tools：

```
用户在 UI 启用/禁用一个 MCP Server
  → tool_mcp_lifecycle.py 更新运行状态
  → tool_mcp_loader.py 热刷新 ToolNode 的工具列表
  → AI 下一轮对话就能/不能用这个能力
```

---

## 与 SaaS 的关系

| 阶段 | 能力来源 | 管理方式 |
|------|---------|---------|
| Phase 1 单机版 | 内置工具 + 用户自行安装 MCP Server | 本地 mcp.json |
| Phase 2 SaaS | 同上 + 云端能力商店 | 云端同步 MCP 配置 |

前端 Vue 组件 + REST API 不变，后端来源不同。
