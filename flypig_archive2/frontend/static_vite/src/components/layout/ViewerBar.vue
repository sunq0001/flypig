<!--
ViewBar：中间查看栏容器

为什么做：用户在中间区域查看文件内容，是 EditorArea 的容器。
实现方法：渲染 EditorArea，透传 openFile 事件。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → layout 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §全局布局
-->
<template>
  <div class="view-bar">
    <EditorArea ref="editorRef" @open-file="$emit('openFile', $event)" />
  </div>
</template>
<script setup>
import { ref } from 'vue'
import EditorArea from '../viewer/EditorArea.vue'

defineEmits(['openFile'])
const editorRef = ref(null)

function openFile(path) {
  editorRef.value?.onOpenFile(path)
}

defineExpose({ openFile })
</script>
<style scoped>
.view-bar{width:100%;height:100%;display:flex;flex-direction:column;overflow:hidden;border-left:1px solid #333}
</style>
