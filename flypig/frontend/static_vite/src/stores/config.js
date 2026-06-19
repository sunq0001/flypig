/**
 * stores/config.js - 全局配置状态管理
 * @module config
 * @description 从 /api/config 获取所有运行时配置，前端不硬编码任何默认值  注意事项： - 初始状态：config 为 null，workspace / model / mode 均为 null
 */

// - fetchConfig() 在 App.vue onMounted 中调用
// - workspace 为 null 时显示 InitWizard，为真时进聊天界面

import { defineStore } from 'pinia'

export const useConfigStore = defineStore('config', {
  state: () => ({
    config: null,        // 原始配置对象，来自 /api/config
  }),

  getters: {
    workspace: (state) => state.config?.workspace ?? null,
    default_model: (state) => state.config?.default_model ?? null,
    models: (state) => state.config?.models ?? [],
    mode: (state) => state.config?.mode ?? null,
    api_configured: (state) => state.config?.api_configured ?? false,
    recent_workspaces: (state) => state.config?.recent_workspaces ?? [],
  },

  actions: {
    async fetchConfig() {
      const res = await fetch('/api/config')
      if (!res.ok) throw new Error(`获取配置失败 (HTTP ${res.status})`)
      this.config = await res.json()
    },

    async setWorkspace(path) {
      const res = await fetch('/api/config/workspace', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || '设置工作区失败')
      }
      const data = await res.json()
      // 更新本地状态，避免重新 fetch
      this.config = { ...this.config, workspace: data.workspace }
    },
  },
})
