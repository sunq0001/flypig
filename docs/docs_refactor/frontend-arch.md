# 前端架构

> **来源**: `architecture-refactor.md` §4
> **关联文档**: `api-reference.md`（SSE 事件格式）、`usage-tracking.md`（response_end 用量数据）
> 新增组件或改 SSE 消费时，需同步检查 api-reference.md。

## 技术栈

- Vue 3 + Vite — 前端框架
- Vercel AI SDK（`@ai-sdk/vue` useChat）— 流式对话 + 工具调用
- Monaco Editor — 代码编辑器
- xterm.js — 用户手动终端
- Element Plus — UI 组件库
- Mermaid.js — 图表渲染（按需加载）
- marked + highlight.js — Markdown 渲染

## 目标目录（20+ .vue 组件）

```
flypig/web/static_vite/
├── package.json
│   dependencies: vue 3.5, ai ^4.2, @ai-sdk/vue ^1.2,
│                 @ai-sdk/openai ^1.3, @ai-sdk/anthropic ^1.1,
│                 xterm ^5.3, xterm-addon-fit ^0.8,
│                 monaco-editor ^0.50
│   devDependencies: vite ^6.0, @vitejs/plugin-vue ^5.0
├── vite.config.js
├── index.html                ← 仅 <div id="app"> + <script> 入口
└── src/
    ├── main.js               ← Vue app.createApp + mount
    ├── App.vue               ← 根组件（三栏布局 + 终端面板）
    │
    ├── style/
    │   ├── variables.css     ← CSS 变量（基础色）
    │   ├── terminal-themes.css ← 终端主题系统
    │   ├── theme-cyberpunk.css   ← 赛博朋克主题覆写
    │   ├── theme-cute.css        ← 可爱风主题覆写
    │   └── base.css          ← 全局样式
    │
    ├── components/
    │   ├── layout/
    │   │   ├── MainLayout.vue    ← 三栏布局容器
    │   │   ├── ResizeHandle.vue  ← 拖拽分割条
    │   │   └── StatusBar.vue     ← 状态栏（模型/用量/主题）
    │   │
    │   ├── sidebar/
    │   │   ├── Sidebar.vue       ← 侧边栏容器
    │   │   ├── Dashboard.vue     ← 首页（最近工作区/快速开始/用量统计）
    │   │   ├── FileTree.vue      ← 递归文件树
    │   │   └── FileTreeNode.vue  ← 单个节点
    │   │
    │   ├── editor/
    │   │   ├── EditorArea.vue    ← 编辑器区域
    │   │   ├── EditorTabs.vue    ← 文件标签页
    │   │   └── MonacoEditor.vue  ← Monaco Editor 封装
    │   │
    │   ├── chat/
    │   │   ├── ChatPanel.vue     ← 对话面板
    │   │   ├── MessageList.vue   ← 消息列表（Vercel AI SDK 驱动）
    │   │   ├── MessageItem.vue   ← 单条消息
    │   │   ├── ThinkingIndicator.vue ← 思考中动画
    │   │   ├── ToolCallCard.vue  ← 工具调用卡片（含审批伪装）
│   │   ├── ChoiceCard.vue    ← Explore 选择题（单选/多选）
│   │   ├── ReasoningView.vue ← AI 推理过程显示（灰字，收到 reasoning 事件时渲染）
│   │   ├── ChangePlanCard.vue ← 改前预览（按 risk 等级：自动/通知/审批）
│   │   ├── ChangeReviewCard.vue ← 改后审查（对比计划与实际）
│   │   ├── SuggestionCard.vue ← 对抗建议卡片（含 ✅/❌ 反馈按钮）
    │   │   ├── MermaidDiagram.vue  ← Mermaid 图表（缩放/下载SVG）
    │   │   ├── LivePreview.vue   ← UI 实时预览（浏览器 SFC 编译）
    │   │   └── InputBox.vue      ← 输入框
    │   │
    │   ├── terminal/
    │   │   ├── TerminalPanel.vue ← 终端面板（单面板，标签页切换）
    │   │   ├── TerminalTab.vue   ← 单个终端标签（PTY/只读输出）
    │   │   ├── XtermViewer.vue   ← xterm.js 封装（用户手动 PTY）
    │   │   └── OutputViewer.vue  ← subprocess 输出查看器（只读，无光标）
    │   │
    │   ├── init/
    │   │   ├── InitWizard.vue    ← 初始化向导
    │   │   ├── WorkspaceStep.vue ← 工作区选择
    │   │   ├── ModelStep.vue     ← 模型选择
    │   │   └── ApiKeyStep.vue    ← API Key 录入
    │   │
    │   └── common/
    │       ├── SensitiveInfoBanner.vue ← 敏感信息标黄警告
    │       ├── MarkdownRender.vue ← Markdown 渲染（扩展 mermaid/tree）
    │       ├── CodeBlock.vue      ← 代码块高亮（highlight.js）
    │       ├── LoadingSpinner.vue ← 加载动画 / 骨架屏
    │       ├── ThemeSwitcher.vue  ← 主题切换（赛博朋克/可爱风）
    │       └── CommandPalette.vue ← Ctrl+K 命令面板
    │
    ├── composables/
    │   ├── useChat.js         ← Vercel AI SDK useChat 封装（核心）
    │   ├── useMessages.js     ← 消息状态管理（辅助 useChat）
    │   ├── useTerminal.js     ← 终端管理（PTY + subprocess 输出标签）
    │   ├── useFileTree.js     ← 文件树状态
    │   ├── useEditor.js       ← Monaco Editor 状态
    │   ├── useLayout.js       ← 面板拖拽分割
    │   ├── useMarkdownRender.js ← 检测 mermaid/html/vue 代码块
    │   ├── useTheme.js        ← 主题切换（data-theme + localStorage）
    │   └── useCommandPalette.js ← Ctrl+K 命令面板（搜索/切换模型/主题）
    │
    └── lib/
        ├── xterm-setup.js     ← xterm.js 初始化
        ├── monaco-setup.js    ← Monaco Editor 配置
        ├── ai-config.js       ← Vercel AI SDK 配置（provider、模型映射）
        └── sfc-compiler.js    ← 浏览器端 Vue SFC 编译（LivePreview 使用）

└── static/                    ← 构建产物（vite build 输出）
    └── ...                     ← server.py 读取此目录，零改动
```

## 竞品对标

核心竞争策略：**功能深度不输大厂 + 个性化风格完胜**。以下体验细节是拉开差距的关键：

### 1. Welcome / Dashboard 首页

InitWizard 之后（或配置存在时）不直接进三栏布局，先展示一个**Dashboard 首页**：

```
┌─────────────────────────────────────────────────────────┐
│  FlyPig                                       🤖 🌗 🔧 │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  最近工作区    │  │  快速开始     │  │  使用统计     │  │
│  │  my-project  │  │  📂 打开项目  │  │  今日 2300   │  │
│  │  stock-app   │  │  ✨ 新建项目  │  │  tokens      │  │
│  │  blog        │  │  📖 快速教程  │  │  ¥0.012     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  [点击任意工作区进入对话]                                 │
└─────────────────────────────────────────────────────────┘
```

- 组件：`Dashboard.vue`（放在 `sidebar/` 或独立视图）
- 展示最近工作区、快速操作、用量概览
- 没有"光秃秃直接进编辑器"的生硬感

### 2. StatusBar 增强

底部的 `StatusBar.vue` 不再只是一个状态文字，改为信息丰富的状态栏：

```
│ 💬 chat  🤖 DeepSeek  ⚡ call: 4  📥 1.5K  📤 0.8K  💰 ¥0.012  🌗 主题 │
```

从左到右：当前模式 / 当前模型 / 本轮用量 / 主题切换快捷入口

### 3. Command Palette（命令面板）

`Ctrl+K` 或 `Cmd+K` 唤出类似 VS Code 的命令面板：

```
┌─────────────────────────────────────┐
│ > 搜索命令...                       │
│                                     │
│  📂 打开工作区                       │
│  🤖 切换模型                        │
│  🎨 切换主题                        │
│  📊 查看用量统计                     │
│  📖 帮助 / 快速教程                  │
│  ⚙️ 设置                            │
└─────────────────────────────────────┘
```

- 组件：`CommandPalette.vue`（放在 `common/`，全局 `Ctrl+K` 唤醒）
- 给用户的"高级感"——做 AI 工具的公司都有这个

### 4. 流畅动画

CSS 过渡 + `vue-transition` 覆盖以下场景：

| 场景 | 效果 | 组件 |
|------|------|------|
| 消息出现 | fade-in + slide-up | MessageItem |
| 卡片出现 | scale-in + shadow 呼吸 | ChoiceCard / SuggestionCard |
| 状态切换 | 柔和 transition | ThemeSwitcher |
| 加载中 | 骨架屏（Skeleton） | ThinkingIndicator 替代方案 |
| 工具调用 | 胶囊式进度条 | ToolCallCard |

### 5. 关键设计总结

- **入口流程**：首次启动 → `InitWizard`（工作区/模型/API Key 三步）→ `Dashboard` 首页 → 进入主界面。配置存在时跳过向导直接进 Dashboard。
- UI 布局不改，只做代码模块化拆分（2500 行 index.html → 20+ .vue 组件）
- Vercel AI SDK `useChat` 替代手写 ReadableStream
- SSE 事件类型与组件映射：`token`→MessageItem, `reasoning`→ReasoningView, `choice`→ChoiceCard, `change_plan`→ChangePlanCard, `change_review`→ChangeReviewCard, `suggestion`→SuggestionCard
- `response_end` 事件携带本轮用量数据（tokens/cache_hit_rate/cost/duration），`MessageItem` 底部渲染一行用量摘要
- 终端面板 = 单面板，标签页混排（PTY 交互标签 + subprocess 只读输出标签）
- **主题切换**：基于 CSS 变量（`data-theme` 属性），不换 UI 库。每个主题对应一个 CSS 文件覆盖变量色值 + 图标色调。通过 `ThemeSwitcher.vue` + `useTheme.js` 切换，选择持久化到 `localStorage`。初始提供默认 / 赛博朋克 / 可爱风三种主题。

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

### useChat 封装（替换手写 SSE）

```javascript
// composables/useChat.js — 用 Vercel AI SDK 接管原来的 SSE 消费逻辑
import { useChat } from '@ai-sdk/vue'

export function useChatComposable() {
  const {
    messages,       // 响应式消息列表（自动管理）
    input,          // 输入框绑定
    handleSubmit,   // 提交处理（自动发送 + 流式接收）
    isLoading,      // 流式进行中状态
    error,          // 错误状态
    stop,           // 中断生成
    append,         // 追加消息
    setMessages,    // 设置历史
  } = useChat({
    api: '/api/chat',           // 后端 SSE 端点
    streamMode: 'stream',       // 流式模式
    headers: { 'Content-Type': 'application/json' },
    onToolCall: (toolCall) => {  // 工具调用自动识别
      showToolCard(toolCall)
    },
    onResponse: (response) => {  // 响应开始回调
      // 清理状态
    },
    onError: (error) => {        // 错误回调
      showError(error)
    },
  })

  return { messages, input, handleSubmit, isLoading, error, stop, append, setMessages }
}
```

**关键变化**：原来要手写 ReadableStream 的 while 循环、SSE 行解析、`handleEvent` dispatch、`_startStreaming` 模拟打字——**全部删除**，让 Vercel AI SDK 一行 `useChat` 搞定。

### 数据流架构（Vercel AI SDK 视角）

```
前端 (Vue 3)
  │
  ├── 用户输入 → InputBox.vue → useChat.handleSubmit()
  │                                   │
  │                                   ├── POST /api/chat (body: {message, tools, ...})
  │                                   │
  │                                   ├── 接收 SSE 流
  │                                   │     ├── text delta  → 自动追加到 messages
  │                                   │     ├── tool_call   → onToolCall 回调
  │                                   │     └── finish      → isLoading = false
  │                                   │
  │                                   └── messages → MessageList.vue 响应式渲染
  │
  ├── MessageList.vue
  │     └── v-for="m in messages"
  │           ├── m.role === 'user'     → 用户消息（已发送）
  │           ├── m.role === 'assistant' → AI 回复（实时流式追加）
  │           └── m.toolInvocations     → 工具调用卡片
  │
  └── 用户手动终端 xterm.js
        └── WebSocket /ws/pty（与 AI 对话完全独立，互不干扰）
        └── WebSocket 接收 workspace:updated 事件（回滚后刷新文件树和编辑器）
```

## 富内容渲染

所有富内容默认内联渲染在对话流中，不弹窗、不开新页。

### 两种类型

| 类型 | 渲染位置 | 组件 | 说明 |
|------|---------|------|------|
| **内联（对话流中）** | AI 消息内，与文字混排 | MermaidDiagram, FileTreeCard | 和卡片一样嵌在消息里 |
| **面板（独立视图）** | 侧边栏/新标签页 | ArchitectureViewer, ImpactGraph | 图表太大时打开独立面板 |

### 实现细节

| 内容类型 | 渲染方式 | 组件 | 交互能力 |
|---------|---------|------|---------|
| **文字 + Markdown** | 内联 | MarkdownRender.vue | 选中复制、代码高亮、行号 |
| **Mermaid 图表** | 内联 | MermaidDiagram.vue (mermaid.js) | 缩放、拖动、下载 SVG |
| **文件树** | 内联 | FileTreeCard.vue | 展开/折叠、点击跳转文件 |
| **架构总览** | 侧边栏面板 | ArchitectureViewer.vue | 点击节点跳转模块 |
| **变更影响图** | 侧边栏面板 | ImpactGraph.vue | 高亮受影响模块 |

### MarkdownRender 扩展

```javascript
// composables/useMarkdownRender.js
import { marked } from 'marked'

const renderer = {
  code({ text, lang }) {
    if (lang === 'mermaid') {
      return `<MermaidDiagram chart="${escapeHtml(text)}" />`
    }
    if (lang === 'tree') {
      return `<FileTreeCard tree="${escapeHtml(text)}" />`
    }
    // 默认：代码高亮
    return `<pre><code class="hljs">${hljs.highlight(text, lang)}</code></pre>`
  }
}
marked.use({ renderer })
```

### Mermaid 按需加载

Mermaid 库只在首次遇到 mermaid 代码块时才动态 import，不增加首屏加载体积。

## InitWizard 初始化向导

启动时的强制初始化流程，按步骤进行：

1. **WorkspaceStep** — 选择工作区目录（输入路径或浏览）
2. **ModelStep** — 选择 AI 模型（DeepSeek / Qwen / GLM / Claude / 自定义 API）
3. **ApiKeyStep** — 输入对应模型的 API Key（支持多个 Key 并存）

三个步骤完成后进入主界面。每个步骤独立验证，不允许跨步骤操作。

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

<script setup>
const fillInput = (opt) => {
  emit('fill-input', opt.label + (opt.desc ? ` (${opt.desc})` : ''));
};
const confirmMulti = () => {
  const text = selectedLabels.value.join(' + ');
  emit('fill-input', text);
};
</script>
```

## LivePreview 组件（UI 实时预览）

AI 生成 Vue SFC 组件代码，在对话中渲染为可交互预览。工作流程：

```
AI: "我建议把文件树从左侧移到顶部导航栏"
    ↓
AI 生成 Vue SFC 代码在代码块中：
  ```vue
  <template>
    <el-menu mode="horizontal">
      <el-menu-item>文件</el-menu-item>
    </el-menu>
  </template>
  ```

用户看到两个内容：
  1. 代码块（语法高亮，可在 Monaco 中编辑）
  2. 代码块上方渲染组件预览（沙箱 iframe，可交互可点击）
```

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

<script setup>
const props = defineProps({ componentCode: String })
const sandboxHtml = computed(() => `
  <!DOCTYPE html>
  <html>
  <head>
    <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"><\/script>
  </head>
  <body>
    <div id="app"></div>
    <script>
      ${compileVueSFC(props.componentCode)}
      app.mount('#app')
    <\/script>
  </body>
  </html>
`)
</script>
```

| 方式 | 用户输入 | AI 输出 | 用户看到 |
|------|---------|---------|---------|
| 主动设计 | "帮我设计一个侧边栏" | 生成 Vue 代码 + 实时预览 | 代码 + 可交互的 UI |
| 功能修改 | "把这个按钮挪到左边" | 修改代码 + 实时更新预览 | 实时看到效果 |
| 代码反馈 | 用户编辑代码块 | AI 看到代码差异后给出建议 | 代码 + 建议文本 |

## 拆分前后对比

| 指标 | 当前（index.html） | 重构后（组件化） |
|------|------------------|----------------|
| 行数 | ~2500 行 | 每组件 ≤120 行 |
| 文件数 | 1 个 | 20+ 个 .vue 文件 |
| 组件数量 | 0 | ~20 个 |
| 全局变量 | 多个（_ptyWs, _terminal 等） | composables 按需导入 |
| 热更新 | 无 | Vite HMR 即时生效 |
