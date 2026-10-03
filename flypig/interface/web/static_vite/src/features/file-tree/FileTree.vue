<!--
FileTree：文件树（融合 @he-tree/vue3 + reliability_app 最佳实践）

参考仓库: https://gitee.com/sunq0001/reliability_app/tree/refactor_ddd/
  → interfaces/web/src/components/folder-tree/

从该方案移植的改进：
  1. 选中色 #04395e（VS Code 蓝色），hover #094771
  2. 箭头 SVG + rotate(90deg) 动画（vs 纯文本）
  3. 引导线颜色 #3c3c3c
-->

<template>
  <div class="file-tree">
    <div class="tree-header">
      <span
        class="tree-root-label"
        @click="$emit('switch-workspace')"
      >{{ rootName }}</span>
      <button
        class="btn-refresh"
        title="刷新文件树"
        @click.stop="doRefresh"
      >
        <span class="refresh-icon">↻</span>
      </button>
    </div>
    <div class="tree-body">
      <BaseTree
        v-if="treeData.length > 0"
        :key="refreshKey"
        :tree-data="treeData"
        :children-lazy-loading="true"
        :children-loader="childrenLoader"
        :default-folded="true"
        :indent="16"
        :virtualization="false"
      >
        <template #default="{ node, tree }">
          <div
            class="vscode-node"
            :class="{
              'is-dir': node.type === NODE_TYPE_DIR,
              'is-selected': selectedPath === node.path
            }"
            @click="onNodeClick(node, tree)"
          >
            <span
              v-if="node.type === NODE_TYPE_DIR"
              class="vscode-arrow"
              :class="{ expanded: !node.$folded }"
              @click.stop="onArrowClick(node, tree)"
            >
              <Icon icon="mdi:chevron-right" />
            </span>
            <span
              v-else
              class="vscode-arrow-spacer"
            />
            <Icon
              class="vscode-icon"
              :icon="getNodeIcon(node)"
            />
            <span class="vscode-name">{{ node.text }}</span>
          </div>
        </template>
      </BaseTree>
      <div
        v-else
        class="tree-empty"
      >
        空白工作区
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { BaseTree } from '@he-tree/vue3'
import '@he-tree/vue3/dist/he-tree-vue3.css'
import { Icon } from '@iconify/vue'
import { useFileEvents } from '@/shared/stores/fileEvents'
import { readDir } from '@/shared/utils/api'
import { getFileIcon } from '@/config/file-icons'

/** 节点类型：目录（后端 /api/tree 返回的 type 字段值） */
const NODE_TYPE_DIR = 'directory'

const props = defineProps({ rootPath: { type: String, default: '' } })
const emit = defineEmits(['open-file', 'switch-workspace'])

const treeData = ref([])
const refreshKey = ref(0)
const selectedPath = ref('')

const rootName = computed(() => {
  if (!props.rootPath) return ''
  const parts = props.rootPath.replace(/\\/g, '/').split('/')
  return parts[parts.length - 1] || props.rootPath
})

function toHeTreeNodes(entries) {
  return entries.map(e => ({
    text: e.name,
    path: e.path,
    type: e.type,
    children: e.type === NODE_TYPE_DIR ? [] : undefined,
  }))
}

async function loadRoot() {
  if (!props.rootPath) return
  try {
    const entries = await readDir(props.rootPath)
    treeData.value = toHeTreeNodes(entries)
  } catch {
    treeData.value = []
  }
}

async function childrenLoader(node) {
  if (node.type !== NODE_TYPE_DIR) return []
  try {
    const entries = await readDir(node.path)
    return toHeTreeNodes(entries)
  } catch {
    return []
  }
}

function onNodeClick(node, tree) {
  if (node.type === NODE_TYPE_DIR) {
    tree.toggleFold(node)
  } else {
    selectedPath.value = node.path
    emit('open-file', node.path)
  }
}

function onArrowClick(node, tree) {
  if (node.type === NODE_TYPE_DIR) {
    tree.toggleFold(node)
  }
}

function getNodeIcon(node) {
  if (node.type === NODE_TYPE_DIR) return 'vscode-icons:default-folder'
  const ext = (node.text || '').split('.').pop()?.toLowerCase()
  return getFileIcon(ext)
}

function doRefresh() {
  refreshKey.value++
  loadRoot()
}

// ── 本地文件变化自动检测 ──
// 不启动轮询（Vite 的 usePolling 已够重），只依赖聊天完成后的主动刷新

watch(() => props.rootPath, loadRoot)
onMounted(() => {
  loadRoot()
  window.addEventListener('flypig:file-tree-refresh', doRefresh)
  // 从其他页面切换回来时自动刷新（比如从文件管理器删了文件切回浏览器）
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onBeforeUnmount(() => {
  window.removeEventListener('flypig:file-tree-refresh', doRefresh)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

// ── 文件变更自动刷新（通过集中式 Store 接收） ──
const { fileChangeVersion } = useFileEvents()
watch(fileChangeVersion, () => {
  doRefresh()
})

// ── 切回页面时自动刷新 ──
function onVisibilityChange() {
  if (!document.hidden) doRefresh()
}
</script>

<style scoped>
.file-tree { font-size: 13px; user-select: none; height: 100%; display: flex; flex-direction: column; }
.tree-header { padding: 8px 12px; font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: .5px; border-bottom: 1px solid #252526; flex-shrink: 0; display: flex; align-items: center; justify-content: space-between; }
.tree-root-label { cursor: pointer; }
.tree-root-label:hover { color: #ccc; }
.btn-refresh { background: none; border: none; color: #666; cursor: pointer; padding: 2px 4px; border-radius: 3px; font-size: 14px; line-height: 1; display: flex; align-items: center; }
.btn-refresh:hover { color: #ccc; background: #2a2d2e; }
.refresh-icon { display: inline-block; }
.refresh-icon:active { animation: spin .3s ease-out; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.tree-body { flex: 1; overflow: auto; }
.tree-body::-webkit-scrollbar { width: 6px; }
.tree-body::-webkit-scrollbar-track { background: transparent; }
.tree-body::-webkit-scrollbar-thumb { background: #424242; border-radius: 3px; }
.tree-empty { color: #666; text-align: center; padding: 24px; font-size: 12px; }

/* VS Code 风格节点 — 移植自 reliability_app */
.vscode-node {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 22px;
  padding-left: 8px;
  cursor: default;
}
.vscode-node:hover { background: #2a2d2e; }
.vscode-node.is-selected { background: #04395e; }
.vscode-node.is-selected:hover { background: #094771; }
.vscode-node.is-dir { cursor: pointer; }

/* 箭头 — SVG chevron-right + rotate(90deg) 动画 */
.vscode-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: #858585;
  transition: transform 0.15s;
}
.vscode-arrow :deep(svg) {
  width: 12px;
  height: 12px;
}
.vscode-arrow.expanded {
  transform: rotate(90deg);
}
.vscode-arrow-spacer {
  width: 16px;
  flex-shrink: 0;
}

/* 文件图标 */
.vscode-icon { flex-shrink: 0; width: 16px; height: 16px; margin-right: 4px; }
.vscode-name { color: #ccc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 0; font-size: 13px; }
.is-selected .vscode-name { color: #fff; }

/* he-tree 覆盖 */
.tree-body :deep(.he-tree) { font-size: 13px; background: #1e1e1e; }
.tree-body :deep(.tree-node-outer) { margin-bottom: 0 !important; }
.tree-body :deep(.tree-node) { padding: 0; background: #1e1e1e; position: relative; z-index: 1; }

/* 缩进引导线 — repeating-linear-gradient 在 padding 区画线
   isolation:isolate 强制 .tree-node-outer 创建独立 stacking context，
   z-index:-1 限制在父级内，不跑到整个页面下面去 */
.tree-body :deep(.tree-node-outer)::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 100%;
  pointer-events: none;
  z-index: -1;
  background: repeating-linear-gradient(
    90deg,
    transparent,
    transparent 15px,
    #3c3c3c 15px,
    #3c3c3c 16px
  );
}
</style>
