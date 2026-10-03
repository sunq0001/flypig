<!--
ThinkingIndicator：思考过程指示器

为什么做：LLM 在"思考"（推理过程）时，用户需要看到进度反馈，不是空白等待。
实现方法：渲染 LLM 返回的 reasoning 事件片段，文字流式出现。
实现效果：用户看到 AI 的思考过程，不会以为卡住了。

技术栈：Vue 3 SFC, SSE reasoning 事件, 逐片段渲染
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/api-reference.md → §reasoning 事件
-->
<template>
  <div class="thinkingIndicator">
    <!-- TODO: implement -->
  </div>
</template>

<script setup>
/**
 * ThinkingIndicator -- TODO: implement component logic
 */
</script>

<style scoped>
.thinkingIndicator { }
</style>
