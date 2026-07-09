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
    <div
      v-if="recentList.length > 0"
      class="recent-section"
    >
      <div class="section-label">
        最近使用的工作区
      </div>
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
        <span class="divider-line" />
        <span class="divider-text">或选择其他目录</span>
        <span class="divider-line" />
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
      <t-button
        size="large"
        @click="openBrowser"
      >
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
    <DirBrowser
      :visible="browserVisible"
      @close="browserVisible = false"
      @select="onBrowserSelect"
    />

    <!-- 错误 -->
    <div
      v-if="error"
      class="error-msg"
    >
      <t-alert
        :message="error"
        theme="error"
      />
    </div>
  </div>
</template>

<script setup>
/**
 * @module WorkspaceStep — 工作区选择
 * @description WorkspaceStep — 工作区选择
 */
import { ref, computed } from 'vue'
import { useConfigStore } from '@/stores/config'
import DirBrowser from './DirBrowser.vue'

const emit = defineEmits(['selected'])
const configStore = useConfigStore()

const recentList = computed(() => configStore.recent_workspaces)

const currentPath = ref('')
const saving = ref(false)
const error = ref(null)

// 弹窗状态
const browserVisible = ref(false)

// ── 最近工作区点击 ──

async function selectWorkspace(path) {
  currentPath.value = path
  try { await confirmPath() } catch { /* confirmPath 内部有 try */ }
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
}

function onBrowserSelect(path) {
  currentPath.value = path
  browserVisible.value = false
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
  color: #cfcfcf;
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
  background: #2f3338;
}

.recent-icon {
  color: #409eff;
  font-size: 18px;
  flex-shrink: 0;
}

.recent-path {
  flex: 1;
  font-size: 13px;
  color: #d4d4d4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: 'Cascadia Code', 'Fira Code', monospace;
  font-size: 12px;
}

.recent-arrow {
  color: #7a7a7a;
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

/* 错误 */
.error-msg {
  margin-top: 4px;
}

/* 统一 TDesign 输入框为深色，适配深色弹窗 */
:deep(.t-input) {
  background-color: #1e1e1e;
  border-color: #3a3a3a;
}
:deep(.t-input__inner) {
  color: #d4d4d4;
}
:deep(.t-input__inner::placeholder) {
  color: #7a7a7a;
}
</style>
