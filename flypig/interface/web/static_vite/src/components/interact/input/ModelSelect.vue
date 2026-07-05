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
      placeholder="模型"
      size="small"
      :popup-props="{ overlayClassName: 'modt-select-popper' }"
      @update:model-value="onSelect"
    >
      <template #prefix>
        <Icon
          v-if="selectedIcon"
          class="selected-icon"
          :icon="selectedIcon"
          :style="{ color: selectedColor }"
        />
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
            <PriceTooltip
              :prices="priceMap[m.value]"
              :symbol="priceSymbol"
              :update-time="priceUpdateTime"
            />
          </template>
          <span class="option-item">
            <Icon
              class="option-icon"
              :icon="m.icon"
              :style="{ color: m.iconColor }"
            />
            <span class="option-name">{{ m.name }}</span>
            <span
              v-if="m.provider"
              class="option-provider"
            >{{ m.provider }}</span>
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
          <Icon
            class="option-icon"
            icon="mdi:laptop"
            style="color:#888"
          />
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
import { getPricing } from '@/utils/api'
import PriceTooltip from './PriceTooltip.vue'
import LocalModelDialog from './LocalModelDialog.vue'
import '../../../style/td-overrides.css'

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
    const priceData = await getPricing(currency.value)
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

