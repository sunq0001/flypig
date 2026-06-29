<!--
BreadcrumbsBar：文件路径面包屑导航

为什么做：用户需要直观地看到当前文件的路径层次，快速导航到上级目录。

实现方法：将 filePath 按分隔符拆分，每段渲染为可点击的 crumb。
点击某段 crumb 可定位到对应目录（后续功能）。

实现效果：类似 VS Code 的面包屑，位于编辑器上方。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → viewer 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
<template>
  <div class="breadcrumbs-bar" v-if="segments.length > 0">
    <span
      v-for="(seg, i) in segments"
      :key="i"
      class="crumb"
      :class="{ 'is-file': i === segments.length - 1 }"
      @click="onCrumbClick(i)"
    >
      <span class="crumb-text">{{ seg.name }}</span>
      <span v-if="i < segments.length - 1" class="crumb-sep">›</span>
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  filePath: { type: String, default: '' },
  rootPath: { type: String, default: '' },
})

const emit = defineEmits(['navigate'])

const segments = computed(() => {
  if (!props.filePath) return []
  // 标准化路径分隔符
  let path = props.filePath.replace(/\\/g, '/')
  let parts = path.split('/').filter(Boolean)

  // 如果 rootPath 已知，尝试截断到工作区根路径开始的相对路径
  if (props.rootPath) {
    const root = props.rootPath.replace(/\\/g, '/').replace(/\/$/, '')
    const idx = path.toLowerCase().indexOf(root.toLowerCase())
    if (idx >= 0) {
      path = path.substring(idx + root.length + 1)
      parts = path.split('/').filter(Boolean)
    }
  }

  return parts.map((name) => ({ name }))
})
</script>

<style scoped>
.breadcrumbs-bar {
  display: flex;
  align-items: center;
  height: 24px;
  padding: 0 12px;
  background: #2d2d2d;
  border-bottom: 1px solid #1e1e1e;
  flex-shrink: 0;
  overflow-x: auto;
  white-space: nowrap;
  gap: 0;
}
.crumb {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 12px;
  color: #999;
  transition: background 0.1s, color 0.1s;
}
.crumb:hover {
  background: #3c3c3c;
  color: #ccc;
}
.crumb.is-file {
  color: #e0e0e0;
  cursor: default;
}
.crumb-sep {
  margin: 0 2px;
  color: #555;
  font-size: 14px;
  line-height: 1;
}
</style>
