<!--
ChatPanel：对话框面板

为什么做：用户与 AI 对话的核心界面，需要展示消息列表和输入框，支持渐进揭露——复杂内容折叠在卡片里。
实现方法：Vue 3 组合 MessageList + InputBox，通过 useChat composable 连接后端 SSE。消息卡片按类型分发（文本/选择/审查/建议/工具调用）。
实现效果：所有对话交互不出面板，代码执行/文件预览/图表渲染都在对话流中完成。

技术栈：Vue 3 SFC, @ai-sdk/vue useChat, Element Plus, marked + highlight.js
层&依赖：frontend.presentation → chat 组件群 + composables/useChat.js
细节见文档：docs/docs_refactor/chat-ux.md → §产品哲学：对话框即是终点
-->
