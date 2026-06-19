<template>
  <div id="flypig-app">
    <!-- 加载中 -->
    <div v-if="loading" class="app-loading">
      <div class="loading-spinner"></div>
      <p>正在连接 FlyPig 服务...</p>
    </div>

    <!-- 连接失败 -->
    <div v-else-if="error" class="app-error">
      <div class="error-icon">⚠</div>
      <h2>连接失败</h2>
      <p>{{ error }}</p>
      <el-button type="primary" @click="retry">重试</el-button>
    </div>

    <!-- 未配置工作区 → 初始化向导 -->
    <InitWizard
      v-else-if="!configStore.workspace"
      @done="onInitDone"
    />

    <!-- 已配置工作区 → 主布局 -->
    <MainLayout v-else :workspace="configStore.workspace">
      <div class="main-placeholder">
        <p>FlyPig Agent</p>
        <p class="sub">选择一个文件或开始对话</p>
      </div>
    </MainLayout>
  </div>
</template>

<script setup>
/**
 * @module 加载中
 * @description 加载中
 */
import { ref, onMounted } from 'vue'
import { useConfigStore } from './stores/config'
import InitWizard from './components/init/InitWizard.vue'
import MainLayout from './components/layout/MainLayout.vue'

const configStore = useConfigStore()
const loading = ref(true)
const error = ref(null)

async function loadConfig() {
  loading.value = true
  error.value = null
  try {
    await configStore.fetchConfig()
  } catch (e) {
    error.value = e.message || '无法连接到后端服务'
  } finally {
    loading.value = false
  }
}

function onInitDone() {
  // workspace 已设置，store 已更新，Vue 自动重渲染
}

function retry() {
  loadConfig()
}

onMounted(() => {
  loadConfig()
})
</script>

<style>
/* 全局样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #1e1e1e;
  color: #ccc;
  min-height: 100vh;
}
#flypig-app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 加载状态 */
.app-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #909399;
  font-size: 14px;
  background: #1e1e1e;
}
.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #333;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 主区域占位文字 */
.main-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #555;
  font-size: 14px;
}
.main-placeholder .sub {
  font-size: 12px;
  color: #444;
}

/* 错误状态 */
.app-error {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-align: center;
  background: #1e1e1e;
}
.error-icon {
  font-size: 48px;
  color: #f56c6c;
}
.app-error h2 {
  font-size: 20px;
  font-weight: 600;
  color: #ccc;
}
.app-error p {
  color: #888;
  font-size: 14px;
  margin-bottom: 8px;
}

</style>
