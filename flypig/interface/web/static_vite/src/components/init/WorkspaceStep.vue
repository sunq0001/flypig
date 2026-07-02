<!--
WorkspaceStep — 工作区选择

注意事项：
- 最近使用的工作区列表（来自后端 /api/config.recent_workspaces），点击直接打开
- "选择文件夹"按钮打开小弹窗目录浏览器（El-Dialog），不使用内嵌树形目录
- 也支持手动输入路径回车确认
-->

<template>
  <div class="workspace-step">
    <!-- 最近使用 -->
    <div v-if="recentList.length > 0" class="recent-section">
      <div class="section-label">最近使用的工作区</div>
      <div class="recent-list">
        <div
          v-for="(ws, idx) in recentList"
          :key="ws + idx"
          class="recent-item"
          @click="selectWorkspace(ws)"
        >
          <span class="recent-icon">📁</span>
          <span class="recent-path">{{ ws }}</span>
          <span class="recent-arrow">→</span>
        </div>
      </div>
      <div class="divider-row">
        <span class="divider-line"></span>
        <span class="divider-text">或选择其他目录</span>
        <span class="divider-line"></span>
      </div>
    </div>

    <!-- 新路径输入 -->
    <div class="path-input-row">
      <t-input
        v-model="currentPath"
        placeholder="输入工作区完整路径，或点击浏览选择..."
        clearable
        size="large"
        @keyup.enter="confirmPath"
      />
      <t-button size="large" @click="openBrowser">
        <span style="margin-right: 4px">📂</span>
        选择文件夹
      </t-button>
    </div>

    <!-- 确认按钮 -->
    <div class="confirm-row">
      <t-button
        theme="primary"
        size="large"
        :disabled="!currentPath"
        :loading="saving"
        style="width: 100%"
        @click="confirmPath"
      >
        使用此目录
      </t-button>
    </div>

    <!-- 目录浏览弹窗 -->
    <div v-if="browserVisible" class="brw-overlay" @click.self="closeBrowser">
      <div class="brw-box">
        <div class="brw-box-header">选择工作区目录</div>
        <div class="brw-body">
          <div class="browser-toolbar">
            <t-button size="small" @click="goUp" :disabled="!parentPath">
              返回上级
            </t-button>
            <t-button size="small" @click="showNewFolderInput">
              新建文件夹
            </t-button>
          </div>

          <div v-if="newFolderVisible" class="new-folder-row">
            <t-input
              v-model="newFolderName"
              placeholder="输入文件夹名称"
              size="small"
              @keyup.enter="createFolder"
            />
            <t-button theme="primary" size="small" @click="createFolder">创建</t-button>
            <t-button size="small" @click="cancelNewFolder">取消</t-button>
          </div>

          <div class="browser-path">{{ browsePath || '...' }}</div>
          <div class="browser-list" :loading="browsing">
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
              <span v-if="entry.type === 'directory'" class="item-hint">点击进入</span>
            </div>
            <div v-if="entries.length === 0 && !browsing" class="browser-empty">
              空目录
            </div>
          </div>
        </div>
        <div class="brw-footer">
          <t-button theme="primary" @click="pickCurrentDir">选择当前目录</t-button>
          <t-button @click="closeBrowser">取消</t-button>
        </div>
      </div>
    </div>

    <!-- 错误 -->
    <div v-if="error" class="error-msg">
      <t-alert :message="error" theme="error" />
    </div>
  </div>
</template>

<script setup>
/**
 * @module WorkspaceStep — 工作区选择
 * @description WorkspaceStep — 工作区选择
 */
import { ref, computed } from 'vue'
import { useConfigStore } from '../../stores/config'

const emit = defineEmits(['selected'])
const configStore = useConfigStore()

const recentList = computed(() => configStore.recent_workspaces)

const currentPath = ref('')
const saving = ref(false)
const error = ref(null)

// 弹窗状态
const browserVisible = ref(false)
const browsePath = ref('')
const entries = ref([])
const parentPath = ref(null)
const browsing = ref(false)
const newFolderVisible = ref(false)
const newFolderName = ref('')

// ── 最近工作区点击 ──

async function selectWorkspace(path) {
  currentPath.value = path
  await confirmPath()
}

// ── 确认路径 ──

async function confirmPath() {
  if (!currentPath.value) return
  saving.value = true
  error.value = null
  try {
    await configStore.setWorkspace(currentPath.value)
    emit('selected')
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

// ── 目录浏览弹窗 ──

async function openBrowser() {
  browserVisible.value = true
  await browse('.')
}

function closeBrowser() {
  browserVisible.value = false
  newFolderVisible.value = false
  newFolderName.value = ''
}

async function browse(path) {
  browsing.value = true
  try {
    const res = await fetch('/api/config/browse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: path || '.' }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.error || `浏览失败 (HTTP ${res.status})`)
    }
    const data = await res.json()
    entries.value = data.entries || []
    parentPath.value = data.parent
    browsePath.value = data.path
  } catch (e) {
    error.value = e.message
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
    const res = await fetch('/api/config/mkdir', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ parent: browsePath.value, name: newFolderName.value }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.error || '创建目录失败')
    }
    newFolderName.value = ''
    newFolderVisible.value = false
    await browse(browsePath.value)
  } catch (e) {
    error.value = e.message
  }
}

function pickCurrentDir() {
  if (browsePath.value) {
    currentPath.value = browsePath.value
    browserVisible.value = false
  }
}
</script>

<style scoped>
.workspace-step {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 最近使用工作区 */
.recent-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label {
  font-size: 13px;
  font-weight: 500;
  color: #606266;
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 240px;
  overflow-y: auto;
}

.recent-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.recent-item:hover {
  background: #ecf5ff;
}

.recent-icon {
  color: #409eff;
  font-size: 18px;
  flex-shrink: 0;
}

.recent-path {
  flex: 1;
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: 'Cascadia Code', 'Fira Code', monospace;
  font-size: 12px;
}

.recent-arrow {
  color: #c0c4cc;
  font-size: 14px;
  flex-shrink: 0;
}

/* 分隔 */
.divider-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 4px 0;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: #e4e7ed;
}

.divider-text {
  font-size: 12px;
  color: #c0c4cc;
  white-space: nowrap;
}

/* 路径输入行 */
.path-input-row {
  display: flex;
  gap: 8px;
}

.path-input-row .t-input {
  flex: 1;
}

/* 确认按钮 */
.confirm-row {
  margin-top: 4px;
}

/* 目录浏览器弹窗 */
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
.brw-body {
  padding: 16px 20px;
}
.brw-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding: 12px 20px;
  border-top: 1px solid #333;
}


.browser-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.new-folder-row {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}

.new-folder-row .t-input {
  flex: 1;
}

.browser-path {
  padding: 6px 8px;
  font-size: 12px;
  color: #909399;
  background: #fafafa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 4px;
  word-break: break-all;
  font-family: monospace;
}

.browser-list {
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  min-height: 80px;
}

.browser-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  cursor: default;
  transition: background 0.15s;
}

.browser-item.is-dir {
  cursor: pointer;
}

.browser-item.is-dir:hover {
  background: #ecf5ff;
}

.item-icon {
  font-size: 16px;
  color: #909399;
  flex-shrink: 0;
}

.item-name {
  flex: 1;
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-hint {
  font-size: 11px;
  color: #c0c4cc;
  flex-shrink: 0;
}

.browser-empty {
  padding: 24px;
  text-align: center;
  color: #c0c4cc;
  font-size: 13px;
}

/* 错误 */
.error-msg {
  margin-top: 4px;
}
</style>
