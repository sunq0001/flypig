<!--
MainLayout：三栏主布局

为什么做：前端 UI 需要三栏结构（侧边栏/编辑区/对话框）+ 底部终端面板和一个状态栏。
实现方法：Vue 3 flex/grid 布局，包含 ResizeHandle 可拖拽调整各栏宽度，StatusBar 显示全局状态。
实现效果：界面布局清晰可调，元素不溢出重叠。

技术栈：Vue 3 SFC, flex/grid, ResizeHandle
层&依赖：frontend.presentation → layout 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
