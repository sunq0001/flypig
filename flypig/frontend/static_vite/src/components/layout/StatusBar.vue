<!--
StatusBar：状态栏

为什么做：用户需要一眼看到当前 AI 模式/模型/用量/主题等全局状态。不需要点开菜单翻找。
实现方法：底部固定状态栏，从左到右展示：当前模式 💬 → 当前模型 🤖 → 本轮用量 ⚡📥📤💰 → 主题切换入口 🌗。
实现效果：全局状态一目了然。

技术栈：Vue 3 SFC, Element Plus icon
层&依赖：frontend.presentation → layout 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §StatusBar 增强
-->
