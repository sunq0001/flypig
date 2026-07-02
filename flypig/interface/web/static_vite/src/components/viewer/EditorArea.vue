<!--
EditorArea：编辑器工作区

为什么做：管理多文件打开/切换/关闭状态，组合 FileBar（标签）和 EditorPane（内容）。
实现方法：接收 openFile 事件添加标签，维护 openFiles/activeFile 状态，
FileBar 显示标签栏，EditorPane 根据文件类型选择渲染器。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → viewer 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §全局布局
-->
<template>
  <div class="editor-area">
    <FileBar :files="openFiles" :active-file="activeFile"
      @select-file="onSelectFile" @close-file="onCloseFile" />
    <EditorPane :file-path="activeFile" />
  </div>
</template>
<script setup>
import { ref } from 'vue'
import FileBar from './FileBar.vue'
import EditorPane from './EditorPane.vue'

const props = defineProps({ initPath: { type: String, default: '' } })
defineEmits(['open-file'])  // 向外透传打开文件事件（后续 AI 调用等场景用）

const openFiles = ref(props.initPath ? [{ path: props.initPath, name: nameFromPath(props.initPath) }] : [])
const activeFile = ref(props.initPath || '')

function nameFromPath(p) {
  return p.replace(/\\/g, '/').split('/').pop()
}

function onOpenFile(path) {
  const name = nameFromPath(path)
  if (!openFiles.value.find(f => f.path === path)) {
    openFiles.value.push({ path, name })
  }
  activeFile.value = path
}

function onSelectFile(path) {
  activeFile.value = path
}

function onCloseFile(path) {
  const idx = openFiles.value.findIndex(f => f.path === path)
  if (idx === -1) return
  openFiles.value.splice(idx, 1)
  if (activeFile.value === path) {
    activeFile.value = openFiles.value[idx]?.path || openFiles.value[idx - 1]?.path || ''
  }
}

// 暴露方法给父组件调用
defineExpose({ onOpenFile })
</script>
<style scoped>
.editor-area{width:100%;height:100%;display:flex;flex-direction:column;overflow:hidden}
</style>
