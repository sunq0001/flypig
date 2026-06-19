<!--
MessageItem：单条消息渲染

为什么做：AI / 用户 / 系统的每条消息需要按角色渲染不同的样式（气泡/卡片）。
实现方法：根据消息角色（user/assistant/system）和事件类型（text/choice/tool_call）分发到对应子组件。
实现效果：消息显示清晰，角色一眼可辨。

技术栈：Vue 3 SFC, marked + highlight.js
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §消息样式
-->
