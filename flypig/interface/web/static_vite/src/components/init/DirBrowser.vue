<!--
DirBrowser：工作区目录浏览器弹窗，从 WorkspaceStep 提取
-->
<template>
  <div
    v-if="visible"
    class="brw-overlay"
    @click.self="$emit('close')"
  >
    <div class="brw-box">
      <div class="brw-box-header">
        选择工作区目录
      </div>
      <div class="brw-body">
        <div class="browser-toolbar">
          <t-button
            size="small"
            :disabled="!parentPath"
            @click="goUp"
          >
            返回上级
          </t-button>
          <t-button
            size="small"
            @click="showNewFolderInput"
          >
            新建文件夹
          </t-button>
        </div>

        <div
          v-if="newFolderVisible"
          class="new-folder-row"
        >
          <t-input
            v-model="newFolderName"
            placeholder="输入文件夹名称"
            size="small"
            @keyup.enter="createFolder"
          />
          <t-button
            theme="primary"
            size="small"
            @click="createFolder"
          >
            创建
          </t-button>
          <t-button
            size="small"
            @click="cancelNewFolder"
          >
            取消
          </t-button>
        </div>

        <div class="browser-path">
          {{ browsePath || '...' }}
        </div>
        <div
          class="browser-list"
          :loading="browsing"
        >
          <div
            v-for="entry in entries"
            :key="entry.name"
            class="browser-item"
            :class="{ 'is-dir': entry.type === 'directory' }"
            @click="entry.type === 'directory' && enterDir(entry.name)"
          >
            <span v-if="entry.type === 'directory'">📁</span>
            <span v-else>📄</span>
            <span class="item-name">{{ entry.name }}</span>
            <span
              v-if="entry.type === 'directory'"
              class="item-hint"
            >点击进入</span>
          </div>
          <div
            v-if="entries.length === 0 && !browsing"
            class="browser-empty"
          >
            空目录
          </div>
        </div>
      </div>
      <div class="brw-footer">
        <t-button
          theme="primary"
          @click="pickCurrentDir"
        >
          选择当前目录
        </t-button>
        <t-button @click="$emit('close')">
          取消
        </t-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { browseDir, mkdirDir } from '@/utils/api'

const props = defineProps({ visible: { type: Boolean, default: false } })
const emit = defineEmits(['close', 'select'])

const browsePath = ref('')
const entries = ref([])
const parentPath = ref(null)
const browsing = ref(false)
const newFolderVisible = ref(false)
const newFolderName = ref('')

watch(() => props.visible, async (v) => {
  if (v) try { await browse('.') } catch { /* browse 内部有 try */ }
})

async function browse(path) {
  browsing.value = true
  try {
    const data = await browseDir(path || '.')
    entries.value = data.entries || []
    parentPath.value = data.parent
    browsePath.value = data.path
  } catch {
    entries.value = []
  } finally {
    browsing.value = false
  }
}

function enterDir(name) {
  if (!browsePath.value) return
  const sep = browsePath.value.endsWith('/') ? '' : '/'
  browse(browsePath.value + sep + name)
}

function goUp() {
  if (parentPath.value) browse(parentPath.value)
}

function showNewFolderInput() {
  newFolderVisible.value = true
  newFolderName.value = ''
  setTimeout(() => {
    const input = document.querySelector('.new-folder-row .t-input__inner')
    if (input) input.focus()
  }, 50)
}

function cancelNewFolder() {
  newFolderVisible.value = false
  newFolderName.value = ''
}

async function createFolder() {
  if (!newFolderName.value || !browsePath.value) return
  try {
    const res = await mkdirDir(browsePath.value, newFolderName.value)
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.error || '创建目录失败')
    }
    newFolderName.value = ''
    newFolderVisible.value = false
    await browse(browsePath.value)
  } catch (e) {
    // error handled by parent
  }
}

function pickCurrentDir() {
  if (browsePath.value) {
    emit('select', browsePath.value)
    emit('close')
  }
}
</script>

<style scoped>
.brw-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3100;
}
.brw-box {
  background: #252526;
  border: 1px solid #333;
  border-radius: 8px;
  width: 520px;
  max-width: 90vw;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.brw-box-header {
  padding: 12px 20px;
  border-bottom: 1px solid #333;
  color: #ccc;
  font-size: 14px;
  font-weight: 500;
}
.brw-body { padding: 16px 20px; }
.brw-footer {
  display: flex; gap: 8px;
  justify-content: flex-end;
  padding: 12px 20px;
  border-top: 1px solid #333;
}
.browser-toolbar { display: flex; gap: 8px; margin-bottom: 8px; }
.new-folder-row { display: flex; gap: 6px; margin-bottom: 8px; }
.new-folder-row .t-input { flex: 1; }
.browser-path {
  padding: 6px 8px; font-size: 12px; color: #909399;
  background: #fafafa; border: 1px solid #e4e7ed;
  border-radius: 4px; margin-bottom: 4px;
  word-break: break-all; font-family: monospace;
}
.browser-list {
  max-height: 220px; overflow-y: auto;
  border: 1px solid #e4e7ed; border-radius: 4px; min-height: 80px;
}
.browser-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px; cursor: default; transition: background 0.15s;
}
.browser-item.is-dir { cursor: pointer; }
.browser-item.is-dir:hover { background: #ecf5ff; }
.item-name {
  flex: 1; font-size: 13px; color: #303133;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.item-hint { font-size: 11px; color: #c0c4cc; flex-shrink: 0; }
.browser-empty { padding: 24px; text-align: center; color: #c0c4cc; font-size: 13px; }
</style>
