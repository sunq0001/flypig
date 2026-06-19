<!--
MemoryBubble：记忆气泡 (P1)

为什么做：AI 回忆起之前对话中的重要知识点时，需要以气泡形式展示，让用户感知 AI 的"记忆"。
实现方法：Vue 3 渲染气泡提示，展示知识点内容和来源轮次。
实现效果：用户感知到 AI 记住上下文，不是每轮从零开始。

技术栈：Vue 3 SFC, 知识点提示
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §记忆气泡
-->
