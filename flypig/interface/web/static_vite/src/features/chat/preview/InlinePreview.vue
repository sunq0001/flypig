<!--
InlinePreview：行内预览

为什么做：AI 生成的代码/图片/表格需要直接在对话框内预览，不需要跳转到其他界面。
实现方法：根据内容类型（code/image/table/echart）选择对应的行内渲染组件。
实现效果：反馈即预览，用户不离开对话流。

技术栈：Vue 3 SFC, highlighted.js, medium-zoom
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §反馈即预览
-->
<template>
  <div class="inlinePreview">
    <!-- TODO: implement -->
  </div>
</template>

<script setup>
/**
 * InlinePreview -- TODO: implement component logic
 */
</script>

<style scoped>
.inlinePreview { }
</style>
