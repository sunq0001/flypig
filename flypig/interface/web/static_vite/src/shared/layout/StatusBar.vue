<!--
StatusBar：底部状态栏

为什么做：用户需要看到当前工作区和全局状态。
实现方法：底部 24px 蓝色条，左侧显示应用名，右侧显示工作区路径。
实现效果：一目了然当前工作环境。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → layout 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §StatusBar
-->
<template>
  <div class="status-bar">
    <span class="status-left">FlyPig Agent</span>
    <span class="status-right">工作区: {{ workspace }}</span>
  </div>
</template>

<script setup>
/**
 * @module StatusBar：底部状态栏
 * @description 用户需要看到当前工作区和全局状态。 底部 24px 蓝色条，左侧显示应用名，右侧显示工作区路径。 一目了然当前工作环境。
 */
defineProps({
  workspace: { type: String, default: '' }
})
</script>

<style scoped>
.status-bar {
  height: 24px;
  background: #007acc;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  font-size: 12px;
  flex-shrink: 0;
}
.status-left, .status-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
