<!--
CommandCard：命令卡片

为什么做：AI 执行的 shell 命令需要以卡片形式展示，包含命令/输出/状态，用户可以看到执行过程。
实现方法：Element Plus card 渲染命令内容/执行状态/输出日志，支持展开/折叠。
实现效果：命令执行过程在对话中透明展示。

技术栈：Vue 3 SFC, Element Plus card
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §渐进揭露
-->
