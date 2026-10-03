<!--
TermBar：终端面板（纯功能组件）

为什么做：用户需要查看 AI 命令执行的终端输出，以及手动终端会话。
实现方法：占位终端区域，后续集成 xterm.js 显示真实终端。
实现效果：InteractBar 切换到终端标签时显示终端输出。

技术栈：Vue 3 SFC, xterm.js
层&依赖：frontend.presentation → terminal 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
<template>
  <div class="term-bar">
    <div class="term-placeholder">终端输出将显示在这里</div>
  </div>
</template>
<style scoped>
.term-bar{flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden}
.term-placeholder{color:#555;font-size:13px}
</style>
