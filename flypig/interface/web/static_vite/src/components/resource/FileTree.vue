<!--
FileTree：文件树（自定义实现，替代TDesign t-tree的渲染问题）

为什么做：TDesign t-tree v1.20.2 有 slot 渲染 bug，改用手动递归渲染。
实现方法：v-for 渲染根节点，目录点击展开/折叠自动加载子节点。
-->

<template>
  <div class="file-tree">
    <div class="tree-header" @click="$emit('switch-workspace')">
      <span class="tree-root-label">{{ rootName }}</span>
    </div>
    <div class="tree-body">
      <TreeNode
        v-for="item in treeData"
        :key="item.path"
        :node="item"
        :depth="0"
        @open-file="p => $emit('open-file', p)"
        @refresh="$emit('refresh')"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import TreeNode from './TreeNode.vue'

const props = defineProps({ rootPath: { type: String, default: '' } })
const emit = defineEmits(['open-file', 'switch-workspace'])

const treeData = ref([])

const rootName = computed(() => {
  if (!props.rootPath) return ''
  const parts = props.rootPath.replace(/\\/g, '/').split('/')
  return parts[parts.length - 1] || props.rootPath
})

async function loadRoot() {
  if (!props.rootPath) return
  const res = await fetch('/api/tree', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: props.rootPath }),
  })
  if (res.ok) {
    const json = await res.json()
    treeData.value = (json.entries || []).map(e => ({ ...e, children: [], loaded: false }))
  }
}

watch(() => props.rootPath, loadRoot)
onMounted(loadRoot)
</script>

<style scoped>
.file-tree { font-size: 13px; user-select: none; height: 100%; display: flex; flex-direction: column; }
.tree-header { padding: 8px 12px; font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: .5px; border-bottom: 1px solid #333; cursor: pointer; flex-shrink: 0; }
.tree-header:hover { color: #aaa; }
.tree-body { flex: 1; overflow: auto; padding: 4px 0; }
</style>
