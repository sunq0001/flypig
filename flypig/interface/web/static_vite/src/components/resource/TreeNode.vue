<!--
TreeNode：文件树的递归节点组件
支持点击展开/折叠目录，点击文件打开预览
-->

<template>
  <div class="tree-node-wrapper">
    <div
      class="tree-node"
      :class="{ 'is-dir': isDir, 'is-open': isDir && expanded }"
      :style="{ paddingLeft: depth * 18 + 8 + 'px' }"
      @click="onClick"
    >
      <span class="node-arrow" v-if="isDir">{{ expanded ? '▾' : '▸' }}</span>
      <span class="node-arrow spacer" v-else></span>
      <Icon class="node-icon" :icon="fileIcon" />
      <span class="node-name">{{ node.name }}</span>
    </div>
    <div v-if="isDir && expanded" class="tree-children">
      <TreeNode
        v-for="child in childrenList"
        :key="child.path"
        :node="child"
        :depth="depth + 1"
        @open-file="p => $emit('open-file', p)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Icon } from '@iconify/vue'

const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 },
})
const emit = defineEmits(['open-file'])

const isDir = computed(() => props.node.type === 'directory')
const expanded = ref(false)
const childrenList = ref(props.node.children || [])
const loading = ref(false)

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

const fileIcon = computed(() => {
  if (isDir.value) return expanded.value ? 'vscode-icons:default-folder-opened' : 'vscode-icons:default-folder'
  const ext = (props.node.name || '').split('.').pop()?.toLowerCase()
  return iconMap[ext] || 'vscode-icons:default-file'
})

async function onClick() {
  if (isDir.value) {
    expanded.value = !expanded.value
    // 懒加载子节点
    if (expanded.value && childrenList.value.length === 0 && !loading.value) {
      loading.value = true
      try {
        const res = await fetch('/api/tree', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: props.node.path }),
        })
        if (res.ok) {
          const json = await res.json()
          childrenList.value = (json.entries || []).map(e => ({ ...e, children: [], loaded: false }))
        }
      } finally {
        loading.value = false
      }
    }
  } else {
    emit('open-file', props.node.path)
  }
}
</script>

<style scoped>
.tree-node-wrapper { }
.tree-node {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 28px;
  cursor: default;
  border-radius: 0;
  transition: background 0.1s;
}
.tree-node:hover { background: #2a2a2a; }
.tree-node.is-dir { cursor: pointer; }
.node-arrow {
  width: 14px;
  flex-shrink: 0;
  text-align: center;
  font-size: 10px;
  color: #888;
}
.node-arrow.spacer { visibility: hidden; }
.node-icon { flex-shrink: 0; width: 16px; height: 16px; color: #888; }
.node-name { font-size: 13px; color: #ccc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 0; }
.tree-children { }
</style>
