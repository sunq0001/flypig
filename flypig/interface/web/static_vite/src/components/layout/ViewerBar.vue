<!--
ViewBar：中间查看栏容器

为什么做：用户在中间区域查看文件内容，是 EditorArea 的容器。
实现方法：渲染 EditorArea，透传 openFile 事件。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → layout 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §全局布局
-->
<template>
  <EditorArea
    ref="editorRef"
    @open-file="$emit('open-file', $event)"
  />
</template>
<script setup>
import { ref } from 'vue'
import EditorArea from '../viewer/EditorArea.vue'

defineEmits(['open-file'])
const editorRef = ref(null)

function openFile(path) {
  editorRef.value?.onOpenFile(path)
}

defineExpose({ openFile })
</script>
<style scoped>
/* border-left 已合并到全局 .panel CSS 中 */
</style>
