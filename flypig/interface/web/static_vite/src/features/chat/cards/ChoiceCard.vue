<!--
ChoiceCard：选择题卡片

为什么做：Explore 模式下 AI 通过选择题收集需求，用户点选而非打字。
实现方法：Element Plus card 渲染 choices 列表，多选/单选模式，选中后通过 useChat.append 发送。
实现效果：点选即交互，不需要打字描述需求。

技术栈：Vue 3 SFC, Element Plus card
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/api-reference.md → §choice 事件, langgraph-graph.md → §Explore 模式
-->
<template>
  <div class="choiceCard">
    <!-- TODO: implement -->
  </div>
</template>

<script setup>
/**
 * ChoiceCard -- TODO: implement component logic
 */
</script>

<style scoped>
.choiceCard { }
</style>
