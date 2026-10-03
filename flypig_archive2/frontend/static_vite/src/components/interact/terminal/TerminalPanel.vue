<!--
TerminalPanel：终端面板容器

为什么做：用户需要独立的手动终端面板执行交互式命令，AI 不注入。
实现方法：Vue 3 容器承载多个 xterm 终端实例 + 标签页切换。
实现效果：用户点击终端标签页打开 xterm，AI 输出展示在只读终端。

技术栈：Vue 3 SFC, xterm.js
层&依赖：frontend.presentation → terminal 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
<template>
  <div class="terminalPanel">
    <!-- TODO: implement -->
  </div>
</template>

<script setup>
/**
 * TerminalPanel -- TODO: implement component logic
 */
</script>

<style scoped>
.terminalPanel { }
</style>
