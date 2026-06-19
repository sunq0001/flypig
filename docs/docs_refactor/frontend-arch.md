# 前端架构

> **历史来源**: `architecture_refactor_old.md` §4
> **关联文档**: `chat-ux.md`（对话框交互设计）、`api-reference.md`（SSE 事件格式）、`folder-tree.md`（完整文件结构）
> 对话框内的交互体验、情绪价值设计、富交互组件清单请见 `chat-ux.md`。

---

## 技术栈

- Vue 3 + Vite — 前端框架
- Vercel AI SDK（`@ai-sdk/vue` useChat）— 流式对话 + 工具调用
- Monaco Editor — 代码编辑器
- xterm.js — 用户手动终端
- Element Plus — UI 组件库
- Mermaid.js — 图表渲染（按需加载）
- marked + highlight.js — Markdown 渲染
- **vue-draggable-next** — 拖拽排序
- **v-viewer** 或 **medium-zoom** — 图片放大预览

## 全局布局（参照 VS Code）

```
┌─────────┬──────────────────┬──────────────────────┬────────┐
│ Activity│  Sidebar          │  Main (Editor Area)   │ Panel  │
│  Bar    │                   │                       │        │
│         │                   │                       │        │
│  📁 文件│  (根据 Activity    │  聊天对话 / 编辑器    │ 终端   │
│  🧩 能力│   切换内容)       │                       │        │
│  📋 任务│                   │                       │        │
│  📊 统计│                   │                       │        │
│  ⚙ 设置│                   │                       │        │
└─────────┴──────────────────┴──────────────────────┴────────┘
```

- **Activity Bar**：左侧图标列，切换 Sidebar 内容
- **Sidebar**：根据 Activity 显示文件树 / 能力管理 / 任务看板等
- **Main Area**：聊天对话（默认）+ 编辑器
- **Panel**：终端 / 输出

## 能力管理面板（参照 VS Code 扩展面板布局）

参考 VS Code Extensions 面板的左右分栏结构：

```
┌─ 能力面板 ─────────────────────────────────────────┐
│                                                      │
│  左侧列表（~40%宽度）         右侧详情（~60%宽度）    │
│  ┌─────────────────┐         ┌────────────────────┐ │
│  │ ◉ 已安装   商店  │         │ 🗄️ 数据库能力       │ │
│  │                  │         │                    │ │
│  │ 🔍 搜索能力...   │         │ v0.3.2 · 860 次调用│ │
│  │                  │         │                    │ │
│  │ 🗄️ 数据库   ✓   │         │ [启用] [设置] [卸载]│ │
│  │ 📖 翻译     ✓   │         │                    │ │
│  │ 🔍 文件搜索 内置 │         │ 可用工具:           │ │
│  │ 🌐 网页抓取 ✓   │         │ ✓ query_db          │ │
│  │                  │         │ ✓ list_tables       │ │
│  │ 📧 邮件          │         │                    │ │
│  │ 📅 日历          │         │ ┌ 配置 ─────────┐  │ │
│  │ 🤖 自动化        │         │ │ 路径: ...     │  │ │
│  └─────────────────┘         │ └───────────────┘  │ │
│                               └────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

> 详细设计见 `mcp.md`

## 目标目录结构

> 完整组件树、composables、lib 见 `folder-tree.md` → `flypig/frontend/static_vite/`。

```
frontend/static_vite/src/
├── main.js                     ← Vue app 挂载
├── App.vue                     ← 根组件（Activity Bar + Sidebar + Main + Panel）
├── style/                      ← 5 个 CSS 文件（变量/主题/base）
├── components/
│   ├── layout/                 ← ★ 布局骨架（ActivityBar, InteractBar, MainLayout, ResizeHandle, StatusBar）
│   ├── resource/               ← ★ 左侧资源栏（ResourceBar, FileTreeBar, McpBar, StatsBar,
│   │                              FileTree, FileTreeNode, McpDashboard/List/Item/Detail/Config/Marketplace）
│   ├── viewer/                 ← ★ 中间查看栏（ViewBar, FileBar, EditorPane,
│   │                              EditorArea, EditorTabs, MonacoEditor,
│   │                              ExcelViewer, PdfViewer, DocxViewer, PptxViewer）
│   ├── chat/                   ← ★ 对话功能（ChatPanel, MessageList, InputBox 等 22 个组件）
│   ├── terminal/               ← ★ 终端功能（TermBar, TerminalPanel, XtermViewer 等 6 个组件）
│   ├── dashboard/              ← 工作区首页（Dashboard）
│   ├── tasks/                  ← 任务看板（TaskBoard）
│   ├── init/                   ← 初始化向导（InitWizard, WorkspaceStep, ModelStep, ApiKeyStep）
│   └── common/                 ← 通用组件（MarkdownRender, CodeBlock, CommandPalette 等 7 个组件）
├── composables/                ← useChat, useFileTree, useLayout, useMcp, useUxEnhancements 等
└── lib/                        ← xterm-setup.js, monaco-setup.js, sfc-compiler.js
```

## Vercel AI SDK 集成

### 为什么用 Vercel AI SDK

| 对比项 | 手写 ReadableStream（当前方案） | Vercel AI SDK（重构方案） |
|--------|-------------------------------|------------------------|
| SSE 解析 | 手写 `reader.read()` 逐行解析 | `useChat` composable 原生支持 |
| 流式状态 | 手动管理 `isStreaming`, `message` | 自动管理，响应式 |
| 工具调用 | 手写 event 分发和卡片渲染 | `useChat` 自动处理 `tool_call` 事件 |
| 错误处理 | 手写 try/catch | 内置重试和错误恢复 |
| 多模型切换 | 改多个地方的 API 调用 | 换 provider 一行代码 |
| 打字机效果 | `setInterval` 模拟 | **原生逐 token 渲染** |
| 输入框禁用/恢复 | 手动 class 切换 | 自动管理 |
| Vue 3 兼容 | ❌ 没有 Vue 原生状态 | ✅ `@ai-sdk/vue` 提供 `useChat` composable |

### useChat 封装

```javascript
// composables/useChat.js — 用 Vercel AI SDK 接管 SSE 消费
import { useChat } from '@ai-sdk/vue'

export function useChatComposable() {
  const { messages, input, handleSubmit, isLoading, error, stop, append, setMessages } = useChat({
    api: '/api/chat',
    streamMode: 'stream',
    headers: { 'Content-Type': 'application/json' },
    onToolCall: (toolCall) => showToolCard(toolCall),
    onResponse: (response) => {},
    onError: (error) => showError(error),
  })

  return { messages, input, handleSubmit, isLoading, error, stop, append, setMessages }
}
```

### 数据流架构

```
前端 (Vue 3)
  │
  ├── 用户输入 → InputBox.vue → useChat.handleSubmit()
  │                                   │
  │                                   ├── POST /api/chat
  │                                   │
  │                                   ├── 接收 SSE 流
  │                                   │     ├── text delta  → messages（自动追加）
  │                                   │     ├── tool_call   → onToolCall 回调
  │                                   │     ├── rich events → EventRouter → 对应组件
  │                                   │     └── finish      → isLoading = false
  │                                   │
  │                                   └── messages → MessageList.vue 响应式渲染
  │
  ├── MessageList.vue
  │     └── v-for="m in messages"
  │           ├── m.role === 'user'      → 用户消息
  │           ├── m.role === 'assistant'  → AI 回复
  │           └── m.richEvents           → 富交互组件（见 chat-ux.md）
  │
  └── 用户手动终端 xterm.js
        └── WebSocket /ws/pty（与 AI 对话完全独立）
```

### EventRouter（新增）— 可扩展接口设计

所有 SSE 富事件通过一个轻量路由器分发。**新增一个组件只需加一行映射 + 一个 .vue 文件**：

```javascript
// composables/useEventRouter.js — 可扩展的事件→组件映射
// 接口约定:
//   - 每个 event 必须有 type 字段
//   - 组件统一 props: { data: Object }
//   - 组件内可自定义交互（按钮/表单/iframe...）

const COMPONENT_MAP = {
  code_exec:        CodeExecBlock,
  inline_preview:   InlinePreview,
  chart:            ChartView,
  data_table:       DataTable,
  command:          CommandCard,
  change_summary:   ChangeSummary,   // ★ 需求级变更叙事（默认）
  change_review:    DiffViewer,      // 代码级 diff（辅助参考，点击展开）
  file_preview:     FilePreview,
  dashboard:        DashboardWidget,
  memory_hint:      MemoryBubble,
  // ★ 扩展点: 新增事件类型只需加一行
  // new_feature:   NewFeatureComponent,
}

// MessageItem.vue 中
<template>
  <div class="message">
    <MarkdownRender :content="message.text" />
    <component
      v-for="ev in message.richEvents"
      :is="COMPONENT_MAP[ev.type]"
      :key="ev.type"
      :data="ev"
    />
  </div>
</template>
```

**扩展步骤（加一个新对话框组件）**：

```
1. 后端 chat_node 中 yield {"type": "new_event", ...}
2. 前端新建 components/chat/NewComponent.vue，接收 props: { data: Object }
3. EventRouter 中加一行映射: new_event: NewComponent,
```

## InitWizard 初始化向导

启动时的工作区选择流程，仅一步：

1. **WorkspaceStep** — 选择工作区目录（输入路径或浏览）
   - POST /api/config/workspace 持久化到 config.yaml
   - 下次启动 GET /api/config 返回 workspace 则跳过 InitWizard

模型选择和 API Key 配置不在 InitWizard 中处理，而是在聊天界面的 model-bar 中：
- 输入框上方 model-bar 显示当前模型名（来自 /api/config.default_model）
- ⚙ 图标弹窗输入 API Key
- 用户点发送时若该模型无 API Key 则弹出输入框，不直接发送
- 每次 POST /api/chat 请求必须带 model 参数，后端拒绝无 model 请求

## ChoiceCard 组件（Explore 选择题）

```
<template>
  <div class="choice-card">
    <p class="choice-question">{{ question }}</p>
    <template v-if="multiSelect">
      <el-checkbox-group v-model="selected">
        <el-checkbox v-for="opt in options" :key="opt.value"
                     :label="opt.value" border class="choice-option">
          <strong>{{ opt.label }}</strong>
          <span class="choice-desc">{{ opt.desc }}</span>
        </el-checkbox>
      </el-checkbox-group>
      <el-button type="primary" @click="confirmMulti"
                 :disabled="selected.length === 0" size="small">确认选择</el-button>
    </template>
    <template v-else>
      <el-button v-for="opt in options" :key="opt.value"
                 @click="fillInput(opt)" class="choice-option">
        <strong>{{ opt.label }}</strong>
        <span class="choice-desc">{{ opt.desc }}</span>
      </el-button>
    </template>
    <p class="choice-hint">或者直接在下方输入框输入你的想法...</p>
  </div>
</template>
```

## LivePreview 组件（UI 实时渲染）

AI 生成的 HTML/Vue SFC 代码在对话中通过 iframe 沙箱渲染为可交互预览：

```vue
<!-- components/chat/LivePreview.vue -->
<template>
  <div class="live-preview">
    <div class="preview-toolbar">
      <span class="preview-title">🔍 实时预览</span>
      <el-button size="small" @click="openInEditor">在编辑器中打开</el-button>
      <el-button size="small" @click="refresh">重新渲染</el-button>
    </div>
    <div class="preview-frame">
      <iframe :srcdoc="sandboxHtml"
              sandbox="allow-scripts allow-same-origin"
              class="preview-iframe" />
    </div>
  </div>
</template>
```

**工作流程**：

| 方式 | 用户输入 | AI 输出 | 用户看到 |
|------|---------|---------|---------|
| 主动设计 | "帮我设计一个侧边栏" | 生成 Vue 代码 + 实时预览 | 代码 + 可交互的 UI |
| 功能修改 | "把这个按钮挪到左边" | 修改代码 + 实时更新预览 | 实时看到效果 |
| 代码反馈 | 用户编辑代码块 | AI 看到代码差异后给出建议 | 代码 + 建议文本 |

## TaskBoard 任务看板

> 完整设计文档见 `mem_convStore_tasks.md`。本节只写前端组件规格。

### 组件树

```
components/
├── chat/
│   └── TaskListCard.vue       ← 对话流中任务状态卡片
├── tasks/
│   └── TaskBoard.vue          ← 侧边栏任务看板
└── common/
    └── TaskHistoryDialog.vue  ← 任务历史弹窗
```

### TaskListCard.vue — 当前方案状态卡片（对话流中）

```
┌─ 当前方案: 重构 auth 模块 ──────────────────┐
│  🔄 重构 auth 路由           [进行中]        │
│  ⬜ 新增 JWT 中间件          [待办]          │
│  ~~编写 auth 测试~~          [已取消]        │
│  ⚡ 修复数据库连接           [已中断]        │
│  ✅ 创建 users 表            [已完成]        │
│                                             │
│  进度: ■■□□□  1/4 完成 · 1 中断 · 1 取消     │
└─────────────────────────────────────────────┘
```

**状态标识**：pending(⬜) / in_progress(🔄) / blocked(⚡) / cancelled(删除线) / completed(✅)

**数据来源**：SSE `task_update` 事件实时更新。

### TaskBoard.vue — 完整任务看板（侧边栏）

侧边栏独立面板，展示当前会话全部任务，支持搜索和回溯快照：

- 搜索栏 + 状态筛选 tabs
- 按时间分组（今天 / 昨天 / 更早）
- 回溯模式顶部提示栏 `🔙 已回到 turn_3 时的状态 [恢复最新]`

### TaskHistoryDialog.vue — 任务生命线（弹窗）

```
┌─ 任务: 重构 auth 路由 ──────────────────────┐
│  🕐 turn_5  创建        → pending           │
│  🕐 turn_5  开始做      → in_progress       │
│  🕐 turn_6  完成        → completed         │
│                                              │
│  关联 checkpoint: turn_6                     │
│  (点击可跳转到该 turn 的回复)                 │
└──────────────────────────────────────────────┘
```

### SSE 事件

```javascript
// 添加任务
{"type": "task_update", "action": "add", "task": {...}}
// 更新状态
{"type": "task_update", "action": "update", "task": {...}}
// 回溯时推送快照
{"type": "tasks_restored", "tasks": [...], "turn_id": 2}
```

---

## 拆分前后对比

| 指标 | 当前（index.html） | 重构后（组件化） |
|------|------------------|----------------|
| 行数 | ~2500 行 | 每组件 ≤120 行 |
| 文件数 | 1 个 | 20+ 个 .vue 文件 |
| 组件数量 | 0 | ~20 个 |
| 全局变量 | 多个（_ptyWs, _terminal 等） | composables 按需导入 |
| 热更新 | 无 | Vite HMR 即时生效 |
