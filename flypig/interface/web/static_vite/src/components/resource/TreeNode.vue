<!--
TreeNode：文件树的递归节点组件
支持点击展开/折叠目录，点击文件打开预览
-->

<template>
  <div class="tree-node-wrapper">
    <div
      class="tree-node"
      :class="{ 'is-dir': isDir, 'is-open': isDir && expanded }"
      :style="{ paddingLeft: depth * INDENT_STEP + BASE_PAD + 'px' }"
      @click="onClick"
    >
      <span
        v-if="isDir"
        class="node-arrow"
      >{{ expanded ? '▾' : '▸' }}</span>
      <span
        v-else
        class="node-arrow spacer"
      />
      <Icon
        class="node-icon"
        :icon="fileIcon"
      />
      <span class="node-name">{{ node.name }}</span>
    </div>
    <div
      v-if="isDir && expanded"
      class="tree-children"
    >
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
import { readDir } from '@/utils/api'
import { getFileIcon } from '@/config/file-icons'

const INDENT_STEP = 18
const BASE_PAD = 8

const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 },
})
const emit = defineEmits(['open-file'])

const isDir = computed(() => props.node.type === 'directory')
const expanded = ref(false)
const childrenList = ref(props.node.children || [])
const loading = ref(false)

const fileIcon = computed(() => {
  if (isDir.value) return expanded.value ? 'vscode-icons:default-folder-opened' : 'vscode-icons:default-folder'
  const ext = (props.node.name || '').split('.').pop()?.toLowerCase()
  return getFileIcon(ext)
})

async function onClick() {
  if (isDir.value) {
    expanded.value = !expanded.value
    // 懒加载子节点
    if (expanded.value && childrenList.value.length === 0 && !loading.value) {
      loading.value = true
      try {
        const entries = await readDir(props.node.path)
        childrenList.value = entries.map(e => ({ ...e, children: [], loaded: false }))
      } catch {
        childrenList.value = []
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
