<!--
TaskListCard：任务列表卡片

为什么做：当前轮次 AI 创建的任务需要以卡片形式展示，用户可以看到本轮的任务拆解。
实现方法：Vue 3 渲染任务列表，显示每个任务的状态（pending/in_progress/completed）。
实现效果：用户看到 AI 说了"帮我做三件事"→卡片上列出三件事及进度。

技术栈：Vue 3 SFC, SSE task_update 事件
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/mem_convStore_tasks.md → §任务状态
-->
<template>
  <div class="taskListCard">
    <!-- TODO: implement -->
  </div>
</template>

<script setup>
/**
 * TaskListCard -- TODO: implement component logic
 */
</script>

<style scoped>
.taskListCard { }
</style>
