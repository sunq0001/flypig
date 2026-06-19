<!--
App：FlyPig 根组件

为什么做：整个前端 UI 的根容器，承载三栏布局（侧边栏/编辑区/对话框）和终端面板。
实现方法：Vue 3 SFC，MainLayout 组合 ResizeHandle + StatusBar，按布局状态动态调整分栏宽度。
实现效果：所有前端功能统一入口，布局可拖拽调整。

技术栈：Vue 3 SFC, Element Plus
层&依赖：frontend.presentation → layout/sidebar/editor/chat/terminal 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
<template></template>
<script setup></script>
<style></style>
