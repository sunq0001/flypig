<!--
FilePreview：文件多类型预览

为什么做：AI 生成或引用的文件（代码/图片/表格/PDF）需要在对话框内预览。
实现方法：根据文件扩展名（.py/.md/.png/.xlsx）选择对应的预览组件。
实现效果：用户点文件直接看到内容，不需要在编辑器中打开。

技术栈：Vue 3 SFC, medium-zoom, marked
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §反馈即预览
-->
<template>
  <div class="filePreview">
    <!-- TODO: implement -->
  </div>
</template>

<script setup>
/**
 * FilePreview -- TODO: implement component logic
 */
</script>

<style scoped>
.filePreview { }
</style>
