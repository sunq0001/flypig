/**
 * config/model-providers.js - 模型厂商配置
 *
 * 从后端 /api/config 的 providers 字段动态加载，
 * 而不是前端硬编码图标/颜色/显示名。
 *
 * 用法：
 *   import { useProviderConfig } from '@/config/model-providers.js'
 *   const { iconMap, colorMap, providerDisplayMap } = useProviderConfig()
 *
 * 所有数据最终来自 flypig/domain/model_ref.py 的 PROVIDERS 字典。
 */

import { computed } from 'vue'
import { useConfigStore } from '@/stores/config.js'

export function useProviderConfig() {
  const store = useConfigStore()

  const iconMap = computed(() => {
    const map = {}
    for (const [key, val] of Object.entries(store.providers)) {
      map[key] = val.icon
    }
    return map
  })

  const colorMap = computed(() => {
    const map = {}
    for (const [key, val] of Object.entries(store.providers)) {
      map[key] = val.color
    }
    return map
  })

  // provider 原始名 → UI 显示名（如 Moonshot → Kimi）
  const providerDisplayMap = computed(() => {
    const map = {}
    for (const [key, val] of Object.entries(store.providers)) {
      map[key] = val.display_name
    }
    return map
  })

  return { iconMap, colorMap, providerDisplayMap }
}
