<!--
ModelSelect：模型选择下拉

props: modelValue — 当前模型名, options — 模型列表（{name, provider} 对象数组）
emits: update:modelValue
使用 t-select 渲染，每个选项带提供商官方图标和价格 tooltip。
-->
<template>
  <t-select
    class="modt-select"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    placeholder="模型"
    size="small"
    :popup-props="{ overlayClassName: 'modt-select-popper' }"
  >
    <template #prefix>
      <Icon v-if="selectedIcon" class="selected-icon" :icon="selectedIcon" :style="{ color: selectedColor }" />
    </template>

    <t-option
      v-for="m in resolvedOptions"
      :key="m.value"
      :value="m.value"
      :label="m.label"
    >
      <t-tooltip
        placement="right"
        :show-after="500"
        :popup-props="{ overlayClassName: 'price-tooltip' }"
        :disabled="!priceMap[m.value]"
      >
        <template #content>
          <table class="price-table">
            <tbody>
              <tr>
                <td class="pt-label">百万tokens输入（缓存未命中）</td>
                <td class="pt-value">${{ priceMap[m.value]?.input.toFixed(3) }}</td>
              </tr>
              <tr v-if="priceMap[m.value]?.input_cache_hit != null">
                <td class="pt-label">百万tokens输入（缓存命中）</td>
                <td class="pt-value">${{ priceMap[m.value]?.input_cache_hit.toFixed(4) }}</td>
              </tr>
              <tr>
                <td class="pt-label">百万tokens输出</td>
                <td class="pt-value">${{ priceMap[m.value]?.output.toFixed(3) }}</td>
              </tr>
            </tbody>
          </table>
          <div class="pt-date">{{ priceUpdated }}</div>
        </template>
        <span class="option-item">
          <Icon class="option-icon" :icon="m.icon" :style="{ color: m.iconColor }" />
          <span class="option-name">{{ m.name }}</span>
          <span class="option-provider">{{ m.provider }}</span>
        </span>
      </t-tooltip>
    </t-option>
  </t-select>

  <!-- 本地模型引导 -->
  <div v-if="showLocalGuide" class="local-guide">
    <div class="lg-title">💻 本地模型</div>
    <div v-if="localStatus.installed?.length" class="lg-hint">
      已安装 {{ localStatus.installed.length }} 个模型，体验 AI 对话
    </div>
    <template v-else-if="localStatus.running">
      <div class="lg-hint">Ollama 已运行，但未安装任何模型</div>
      <div v-for="s in localStatus.suggestions" :key="s.name" class="lg-item">
        <span class="lg-name">{{ s.name }}</span>
        <span class="lg-size">{{ s.size }}</span>
        <span class="lg-desc">{{ s.description }}</span>
        <t-button size="small" @click="pullModel(s.name)" :loading="pullingName === s.name">下载</t-button>
      </div>
    </template>
    <div v-else class="lg-hint">
      Ollama 未运行，<a href="https://ollama.com/download" target="_blank">下载 Ollama</a>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Icon } from '@iconify/vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
})
defineEmits(['update:modelValue'])

const priceMap = ref({})
const priceUpdated = ref('')
const localStatus = ref({ running: false, installed: [], suggestions: [] })
const pullingName = ref('')

const showLocalGuide = computed(() => {
  return localStatus.value.running || localStatus.value.installed?.length > 0
})

onMounted(async () => {
  try {
    const [priceRes, localRes] = await Promise.all([
      fetch('/api/pricing'),
      fetch('/api/config/local-models'),
    ])
    const priceData = await priceRes.json()
    priceMap.value = priceData.prices || {}
    priceUpdated.value = priceData.updated || ''
    localStatus.value = await localRes.json()
  } catch { /* 获取失败不影响核心功能 */ }
})

async function pullModel(name) {
  pullingName.value = name
  try {
    await fetch('/api/config/local-models/pull', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: name }),
    })
    // 轮询等待模型下载完成
    const poll = setInterval(async () => {
      const res = await fetch('/api/config/local-models')
      const data = await res.json()
      if (data.installed?.includes(name)) {
        localStatus.value = data
        pullingName.value = ''
        clearInterval(poll)
      }
    }, 5000)
  } catch {
    pullingName.value = ''
  }
}

const iconMap = {
  DeepSeek: 'simple-icons:deepseek',
  OpenAI: 'simple-icons:openai',
  Anthropic: 'simple-icons:anthropic',
  Qwen: 'simple-icons:alibabadotcom',
  Tencent: 'simple-icons:tencentqq',
  ByteDance: 'simple-icons:tiktok',
  Moonshot: 'simple-icons:quantconnect',
  ZhipuAI: 'simple-icons:zotero',
  Local: 'mdi:laptop',
}

const colorMap = {
  DeepSeek: '#4F6EF7',
  OpenAI: '#74AA9C',
  Anthropic: '#D4A574',
  Qwen: '#FF6A00',
  Tencent: '#1479D1',
  ByteDance: '#000000',
  Moonshot: '#6C5CE7',
  ZhipuAI: '#0E7AFF',
  Local: '#888',
}

const resolvedOptions = computed(() => {
  return props.options.map(o => {
    if (typeof o === 'string') return { value: o, label: o, icon: 'mdi:robot', iconColor: '#888', name: o, provider: '' }
    return {
      value: o.name,
      label: `${o.name} (${o.provider})`,
      icon: iconMap[o.provider] || 'mdi:robot-outline',
      iconColor: colorMap[o.provider] || '#888',
      name: o.name,
      provider: o.provider,
    }
  })
})

const selectedInfo = computed(() => {
  const found = resolvedOptions.value.find(m => m.value === props.modelValue)
  return found ? { icon: found.icon, color: found.iconColor } : { icon: null, color: '#888' }
})
const selectedIcon = computed(() => selectedInfo.value.icon)
const selectedColor = computed(() => selectedInfo.value.color)
</script>

<style scoped>
.modt-select {
  width: auto;
  min-width: 200px;
}
.modt-select :deep(.t-select__wrapper) {
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 4px;
  min-height: 20px;
}
.modt-select :deep(.t-select__placeholder) {
  color: #888;
  font-size: 11px;
}
.modt-select :deep(.t-select__selected-item) {
  font-size: 11px;
  color: #888;
  flex: 1;
  min-width: 0;
}
.modt-select :deep(.t-select__selected-item > span) {
  overflow: hidden;
  text-overflow: ellipsis;
}
.modt-select :deep(.t-select__caret) {
  color: #555;
  font-size: 10px;
}
.selected-icon {
  font-size: 14px;
  color: #bbb;
  display: inline-flex;
  margin-right: 2px;
}
.local-guide {
  padding: 8px 12px;
  border-top: 1px solid #333;
  margin-top: 4px;
}
.lg-title { font-size: 12px; color: #888; margin-bottom: 4px; }
.lg-hint { font-size: 11px; color: #666; margin-bottom: 6px; }
.lg-hint a { color: #409eff; text-decoration: none; }
.lg-item {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 0; font-size: 11px;
}
.lg-name { color: #ccc; white-space: nowrap; }
.lg-size { color: #888; }
.lg-desc { flex: 1; color: #666; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>

<style>
.modt-select-popper {
  background: #252526 !important;
  border: 1px solid #333 !important;
  min-width: 260px !important;
}
.modt-select-popper .t-select-dropdown__item {
  padding: 2px 8px;
  height: auto;
  background: transparent !important;
  color: #ccc;
}
.modt-select-popper .t-select-dropdown__item:hover,
.modt-select-popper .t-select-dropdown__item.hover {
  background: #3c3c3c !important;
}
.modt-select-popper .t-select-dropdown__item.is-selected {
  color: #409eff !important;
}
.modt-select-popper .t-popup__arrow::before {
  background: #252526 !important;
  border-color: #333 !important;
}
.option-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  width: 100%;
}
.option-icon {
  font-size: 16px;
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.option-name {
  color: #eee;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.option-provider {
  color: #666;
  font-size: 10px;
  margin-left: auto;
  flex-shrink: 0;
  padding-left: 8px;
}
.price-tooltip {
  background: #2a2a2a !important;
  border: 1px solid #444 !important;
  padding: 6px 8px !important;
}
.price-tooltip .t-popup__arrow::before {
  background: #2a2a2a !important;
  border-color: #444 !important;
}
.price-table {
  border-collapse: collapse;
  white-space: nowrap;
}
.price-table td {
  padding: 1px 4px;
  font-size: 11px;
  line-height: 1.6;
}
.pt-label {
  color: #999;
  padding-right: 12px;
}
.pt-value {
  color: #eee;
  font-weight: 600;
  font-family: monospace;
  text-align: right;
}
.pt-date {
  margin-top: 3px;
  padding-top: 3px;
  border-top: 1px solid #3a3a3a;
  color: #666;
  font-size: 10px;
  text-align: right;
}
</style>
