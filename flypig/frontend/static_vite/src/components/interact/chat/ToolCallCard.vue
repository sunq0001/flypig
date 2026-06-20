<!--
ToolCallCard：工具调用卡片

为什么做：AI 调用工具时（读文件/执行命令），需要展示调用的工具名和参数、执行状态、沙箱/本地标识。
实现方法：Vue 3 卡片式渲染，显示 tool_name/arguments/status/result，沙箱内执行时显示🔒标识。
实现效果：用户看到 AI 正在做什么工具操作，执行结果透明。

技术栈：Vue 3 SFC, 沙箱/本地标识, SSE tool_call 事件
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §工具调用
-->
<template>
  <div class="toolCallCard">
    <!-- TODO: implement -->
  </div>
</template>

<script setup>
/**
 * ToolCallCard -- TODO: implement component logic
 */
</script>

<style scoped>
.toolCallCard { }
</style>
