<!--
FileTree：文件树（基于 Element Plus el-tree）

为什么做：用户需要直观地看到工作区的文件和目录结构。
实现方法：使用 el-tree 的 lazy 懒加载 + #default slot 自定义节点。
expand-on-click-node 默认支持点击展开/折叠，自带箭头图标。
CSS 伪元素绘制 VS Code 风格的缩进连接线。

技术栈：Vue 3 SFC, Element Plus Tree
层&依赖：frontend.presentation → resource 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
<template>
  <div class="file-tree">
    <div class="tree-header" @click="$emit('switchWorkspace')">
      <span class="tree-root-label">{{ rootName }}</span>
    </div>
    <el-tree
      ref="treeRef"
      :data="treeData"
      :props="treeProps"
      :lazy="true"
      :load="loadNode"
      node-key="path"
      :expand-on-click-node="true"
      :indent="20"
      highlight-current
      class="file-el-tree"
    >
      <template #default="{ node, data }">
        <span class="node-wrap" @click="onNodeClick(data)">
          <Icon class="node-icon" :icon="fileIcon(data)" />
          <span class="node-name">{{ data.name }}</span>
        </span>
      </template>
    </el-tree>
  </div>
</template>
<script setup>
/**
 * @module FileTree — 文件树（el-tree 实现）
 * @description 使用 Element Plus el-tree 的 lazy 懒加载，自带点击展开/折叠和箭头。
 */
import { ref, computed, watch, onMounted } from 'vue'
import { Icon } from '@iconify/vue'

const props = defineProps({ rootPath: { type: String, default: '' } })
const emit = defineEmits(['openFile', 'switchWorkspace'])

const treeRef = ref(null)
const treeData = ref([])

const iconMap = {
  js: 'vscode-icons:file-type-js', ts: 'vscode-icons:file-type-typescript',
  vue: 'vscode-icons:file-type-vue', py: 'vscode-icons:file-type-python',
  json: 'vscode-icons:file-type-json', md: 'vscode-icons:file-type-markdown',
  html: 'vscode-icons:file-type-html', css: 'vscode-icons:file-type-css',
  yml: 'vscode-icons:file-type-yaml', yaml: 'vscode-icons:file-type-yaml',
  toml: 'vscode-icons:file-type-toml',
  png: 'vscode-icons:file-type-image', jpg: 'vscode-icons:file-type-image',
  jpeg: 'vscode-icons:file-type-image', svg: 'vscode-icons:file-type-image',
  txt: 'vscode-icons:file-type-text',
  gitignore: 'vscode-icons:file-type-git',
}

function fileIcon(data) {
  if (data.type === 'directory') return 'vscode-icons:default-folder'
  const ext = (data.name || '').split('.').pop()?.toLowerCase()
  return iconMap[ext] || 'vscode-icons:default-file'
}

const treeProps = { children: 'children', label: 'name', isLeaf: 'isLeaf' }

const rootName = computed(() => {
  if (!props.rootPath) return ''
  const parts = props.rootPath.replace(/\\/g, '/').split('/')
  return parts[parts.length - 1] || props.rootPath
})

async function fetchDir(path) {
  const res = await fetch('/api/tree', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  })
  if (!res.ok) return []
  const json = await res.json()
  return (json.entries || []).map(e => ({
    ...e,
    children: undefined,
    isLeaf: e.type === 'file',
  }))
}

async function loadNode(node, resolve) {
  const path = node?.data?.path || props.rootPath
  const children = await fetchDir(path)
  resolve(children)
}

function onNodeClick(data) {
  if (data.type === 'file') emit('openFile', data.path)
  // 目录: el-tree 自带 expand-on-click-node 处理
}

async function loadRoot() {
  if (!props.rootPath) return
  const children = await fetchDir(props.rootPath)
  treeData.value = children || []
}

watch(() => props.rootPath, loadRoot)
onMounted(loadRoot)
</script>
<style scoped>
.file-tree{font-size:13px;user-select:none;height:100%;display:flex;flex-direction:column}
.tree-header{padding:8px 12px;font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #333;cursor:pointer;flex-shrink:0}
.tree-header:hover{color:#aaa}
.file-el-tree{flex:1;overflow:auto;background:transparent;padding:4px 0}
.node-wrap{display:flex;align-items:center;gap:4px;width:100%}
.node-icon{flex-shrink:0;width:18px;height:18px;color:#888}
.node-name{font-size:13px;color:#ccc;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0}
</style>
<style>
/* 全局样式：el-tree 暗色主题 + 缩进连接线 */
.file-el-tree .el-tree-node__content {
  height: 28px;
  background: transparent !important;
}
.file-el-tree .el-tree-node__content:hover {
  background: #2a2a2a !important;
}
.file-el-tree .el-tree-node:focus > .el-tree-node__content {
  background: #2a2a2a !important;
}
.file-el-tree .el-tree-node__expand-icon {
  color: #888;
  font-size: 12px;
}
.file-el-tree .el-tree-node__expand-icon.is-leaf {
  color: transparent;
}
/* 缩进连接线 */
.file-el-tree .el-tree-node {
  position: relative;
}
.file-el-tree .el-tree-node::before {
  content: '';
  position: absolute;
  left: -10px;
  top: -50%;
  bottom: 50%;
  border-left: 1px solid #333;
}
.file-el-tree .el-tree-node::after {
  content: '';
  position: absolute;
  left: -10px;
  top: 14px;
  width: 10px;
  border-bottom: 1px solid #333;
}
.file-el-tree .el-tree-node:last-child::before {
  height: 14px;
}
.file-el-tree > .el-tree-node::before,
.file-el-tree > .el-tree-node::after {
  display: none;
}
</style>
