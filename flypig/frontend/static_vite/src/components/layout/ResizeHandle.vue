<!--
ResizeHandle：分栏拖拽手柄

为什么做：用户需要拖拽调整三栏布局各栏宽度，满足不同的工作需求（写代码时编辑区宽、聊天时对话框宽）。
实现方法：vue-draggable-next 实现拖拽手柄，拖拽时调整相邻两栏的宽度比例。
实现效果：布局灵活适应不同工作场景。

技术栈：Vue 3 SFC, vue-draggable-next
层&依赖：frontend.presentation → layout 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §布局
-->
