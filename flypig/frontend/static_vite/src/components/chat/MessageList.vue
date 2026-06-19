<!--
MessageList：消息列表

为什么做：AI 对话生成的消息需要列表展示，支持虚拟滚动和自动滚动到底部。
实现方法：Vue 3 虚拟滚动列表，自动滚动到最新消息，按角色分组渲染。
实现效果：长对话不卡顿，新消息自动可见。

技术栈：Vue 3 SFC, Element Plus virtualized list
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §渐进揭露
-->
