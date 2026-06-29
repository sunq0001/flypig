<!--
ModelSelect：模型选择下拉

props: modelValue — 当前模型名, options — 模型列表（{name, provider} 对象数组）
emits: update:modelValue
使用 el-select 渲染，每个选项带提供商官方图标和价格 tooltip。
-->
<template>
  <el-select
    class="model-select"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    placeholder="模型"
    size="small"
    popper-class="model-select-popper"
  >
    <template #prefix>
      <Icon v-if="selectedIcon" class="selected-icon" :icon="selectedIcon" :style="{ color: selectedColor }" />
    </template>

    <el-option
      v-for="m in resolvedOptions"
      :key="m.value"
      :value="m.value"
      :label="m.label"
    >
      <el-tooltip
        placement="right"
        :show-after="500"
        popper-class="price-tooltip"
        :disabled="!priceMap[m.value]"
      >
        <template #content>
          <table class="price-table">
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
          </table>
          <div class="pt-date">{{ priceUpdated }}</div>
        </template>
        <span class="option-item">
          <Icon class="option-icon" :icon="m.icon" :style="{ color: m.iconColor }" />
          <span class="option-name">{{ m.name }}</span>
          <span class="option-provider">{{ m.provider }}</span>
        </span>
      </el-tooltip>
    </el-option>
  </el-select>
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

onMounted(async () => {
  try {
    const res = await fetch('/api/pricing')
    const data = await res.json()
    priceMap.value = data.prices || {}
    priceUpdated.value = data.updated || ''
  } catch { /* 定价获取失败不影响功能 */ }
})

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
.model-select {
  width: auto;
  min-width: 200px;
}
.model-select :deep(.el-select__wrapper) {
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 4px;
  min-height: 20px;
}
.model-select :deep(.el-select__placeholder) {
  color: #888;
  font-size: 11px;
}
.model-select :deep(.el-select__selected-item) {
  font-size: 11px;
  color: #888;
  flex: 1;
  min-width: 0;
}
.model-select :deep(.el-select__selected-item > span) {
  overflow: hidden;
  text-overflow: ellipsis;
}
.model-select :deep(.el-select__caret) {
  color: #555;
  font-size: 10px;
}
.selected-icon {
  font-size: 14px;
  color: #bbb;
  display: inline-flex;
  margin-right: 2px;
}
</style>

<style>
.model-select-popper {
  background: #252526 !important;
  border: 1px solid #333 !important;
  min-width: 260px !important;
}
.model-select-popper .el-select-dropdown__item {
  padding: 2px 8px;
  height: auto;
  background: transparent !important;
  color: #ccc;
}
.model-select-popper .el-select-dropdown__item:hover,
.model-select-popper .el-select-dropdown__item.hover {
  background: #3c3c3c !important;
}
.model-select-popper .el-select-dropdown__item.is-selected {
  color: #409eff !important;
}
.model-select-popper .el-popper__arrow::before {
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
.price-tooltip .el-popper__arrow::before {
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
