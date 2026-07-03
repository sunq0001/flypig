<!--
ModelSelect：模型选择下拉

props: modelValue — 当前模型名, options — 模型列表（{name, provider} 对象数组）
emits: update:modelValue

变化：本地模型不再直接出现在下拉列表中，
统一由 "💻 本地模型" 入口打开 Dialog 选择。
-->
<template>
  <div class="modt-select-wrap">
    <t-select
      class="modt-select"
      :model-value="modelValue"
      @update:model-value="onSelect"
      placeholder="模型"
      size="small"
      :popup-props="{ overlayClassName: 'modt-select-popper' }"
    >
      <template #prefix>
        <Icon v-if="selectedIcon" class="selected-icon" :icon="selectedIcon" :style="{ color: selectedColor }" />
      </template>

      <t-option
        v-for="m in cloudOptions"
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
                  <td class="pt-value">{{ priceSymbol }} {{ priceMap[m.value]?.input?.toFixed(3) }}</td>
                </tr>
                <tr v-if="priceMap[m.value]?.input_cache_hit != null">
                  <td class="pt-label">百万tokens输入（缓存命中）</td>
                  <td class="pt-value">{{ priceSymbol }} {{ priceMap[m.value]?.input_cache_hit?.toFixed(4) }}</td>
                </tr>
                <tr>
                  <td class="pt-label">百万tokens输出</td>
                  <td class="pt-value">{{ priceSymbol }} {{ priceMap[m.value]?.output?.toFixed(3) }}</td>
                </tr>
              </tbody>
            </table>
            <div class="pt-date">更新于 {{ priceUpdateTime }}</div>
          </template>
          <span class="option-item">
            <Icon class="option-icon" :icon="m.icon" :style="{ color: m.iconColor }" />
            <span class="option-name">{{ m.name }}</span>
            <span v-if="m.provider" class="option-provider">{{ m.provider }}</span>
          </span>
        </t-tooltip>
      </t-option>

      <!-- 分隔线 + 本地模型入口 -->
      <t-option
        value="__local__"
        label="💻 本地模型"
        class="local-entry"
      >
        <span class="option-item">
          <Icon class="option-icon" icon="mdi:laptop" style="color:#888" />
          <span class="option-name">💻 本地模型</span>
        </span>
      </t-option>
    </t-select>

    <LocalModelDialog
      :visible="showLocalDialog"
      @close="showLocalDialog = false"
      @select="onLocalModelSelect"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import { useProviderConfig } from '@/config/model-providers.js'
import LocalModelDialog from './LocalModelDialog.vue'

const { iconMap, colorMap, providerDisplayMap } = useProviderConfig()

const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

const priceMap = ref({})
const priceUpdateTime = ref('')
const currency = ref('USD')
const priceSymbol = computed(() => currency.value === 'CNY' ? '¥' : '$')
const showLocalDialog = ref(false)

onMounted(async () => {
  try {
    const lang = navigator.language || ''
    currency.value = lang.startsWith('zh') ? 'CNY' : 'USD'
    const priceRes = await fetch(`/api/pricing?currency=${currency.value}`)
    const priceData = await priceRes.json()
    priceMap.value = priceData.prices || {}
    priceUpdateTime.value = priceData.update_time || ''
  } catch { /* */ }
})

function onSelect(value) {
  if (value === '__local__') {
    showLocalDialog.value = true
    return // 不 emit，保持当前选中不变
  }
  emit('update:modelValue', value)
}

function onLocalModelSelect(modelName) {
  emit('update:modelValue', modelName)
}

// 仅渲染云端模型（过滤掉 local: true）
const cloudOptions = computed(() => {
  return props.options
    .filter(o => !o.local)
    .map(o => {
      if (typeof o === 'string') return { value: o, label: o, icon: 'mdi:robot', iconColor: '#888', name: o, provider: '' }
      const rawProvider = o.provider
      const displayProvider = providerDisplayMap.value[rawProvider] || rawProvider
      const nameLower = o.name.toLowerCase()
      const providerLower = rawProvider.toLowerCase()
      const isRedundant = nameLower.includes(providerLower)
      return {
        value: o.name,
        label: isRedundant ? o.name : `${o.name} (${displayProvider})`,
        icon: iconMap.value[displayProvider] || iconMap.value[rawProvider] || 'mdi:robot-outline',
        iconColor: colorMap.value[displayProvider] || colorMap.value[rawProvider] || '#888',
        name: o.name,
        provider: isRedundant ? '' : displayProvider,
      }
    })
})

const selectedInfo = computed(() => {
  const allOptions = [...cloudOptions.value]
  const isLocal = props.options.find(m => m.name === props.modelValue)?.local
  if (isLocal) {
    return { icon: 'mdi:laptop', color: '#888' }
  }
  const found = allOptions.find(m => m.value === props.modelValue)
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
.modt-select :deep(.t-input) {
  background: transparent !important;
  box-shadow: none !important;
  border-color: #444 !important;
  border-radius: 6px;
}
.modt-select :deep(.t-input:hover) {
  border-color: #555 !important;
}
.modt-select :deep(.t-input.t-is-focused),
.modt-select :deep(.t-is-focused > .t-input) {
  border-color: #666 !important;
  box-shadow: none !important;
}
.modt-select :deep(.t-select__wrapper),
.modt-select :deep(.t-select-input),
.modt-select :deep(.t-input__wrap),
.modt-select :deep(.t-input__inner) {
  background: transparent !important;
  box-shadow: none !important;
  color: #eee !important;
  caret-color: #eee;
}
.modt-select :deep(.t-select__placeholder) {
  color: #777;
  font-size: 11px;
}
.modt-select :deep(.t-select__selected-item) {
  font-size: 11px;
  color: #ddd;
  flex: 1;
  min-width: 0;
}
.modt-select :deep(.t-select__selected-item > span) {
  overflow: hidden;
  text-overflow: ellipsis;
}
.modt-select :deep(.t-select__caret),
.modt-select :deep(.t-input__suffix-icon svg),
.modt-select :deep(.t-input__suffix-icon path),
.modt-select :deep(.t-input__suffix-icon) {
  color: #999 !important;
  fill: currentColor !important;
}
.selected-icon {
  font-size: 14px;
  color: #bbb;
  display: inline-flex;
  margin-right: 2px;
}
</style>

<style>
.modt-select-popper {
  background: #252526 !important;
  border: 1px solid #333 !important;
  min-width: 260px !important;
  --td-bg-color-container: #252526;
  --td-bg-color-container-hover: #3c3c3c;
  --td-bg-color-container-active: #2a2a2a;
  --td-bg-color-specialcomponent: #252526;
  --td-brand-color: #409eff;
  --td-brand-color-light: rgba(64, 158, 255, 0.12);
  --td-brand-color-light-hover: rgba(64, 158, 255, 0.2);
  --td-text-color-primary: #e5e5e5;
  --td-text-color-secondary: #999;
  --td-component-stroke: #444;
  --td-border-level-1-color: #444;
  --td-font-gray-1: #eee;
  --td-font-gray-2: #bbb;
  --td-success-color: #52c41a;
  --td-warning-color: #faad14;
  --td-error-color: #ff4d4f;
}
.modt-select-popper .t-popup__content,
.modt-select-popper .t-select-dropdown-inner,
.modt-select-popper .t-select-option-list,
.modt-select-popper .t-select-dropdown,
.modt-select-popper .t-select__list,
.modt-select-popper ul {
  background: #252526 !important;
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
.modt-select-popper .t-select-dropdown__item,
.modt-select-popper .t-select-option {
  color: #e5e5e5 !important;
}
.modt-select-popper .t-select-dropdown__item.is-selected,
.modt-select-popper .t-option.t-is-selected,
.modt-select-popper .t-select-option.t-is-selected {
  color: #409eff !important;
  background: #2a2a2a !important;
}
.modt-select-popper .t-popup__arrow::before {
  background: #252526 !important;
  border-color: #333 !important;
}
.modt-select-popper,
.modt-select-popper .t-popup__content {
  background: #252526 !important;
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
/* 本地模型入口分隔样式 */
.local-entry {
  border-top: 1px solid #333;
  margin-top: 2px;
}
.local-entry .option-name {
  color: #888;
  font-size: 11px;
}
</style>
