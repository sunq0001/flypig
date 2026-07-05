<!--
ModeSelect：Explore / Plan / Execute 模式选择下拉

props: modelValue — 当前模式值
emits: update:modelValue
-->
<template>
  <t-select
    class="mode-select"
    :model-value="modelValue"
    size="small"
    :popup-props="{ overlayClassName: 'mode-select-popper' }"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <t-option
      value="explore"
      label="🔍 Explore"
    />
    <t-option
      value="plan"
      label="📋 Plan"
    />
    <t-option
      value="execute"
      label="⚡ Execute"
    />
  </t-select>
</template>

<script setup>
import '../../../style/td-overrides.css'
defineProps({ modelValue: { type: String, default: 'explore' } })
defineEmits(['update:modelValue'])
</script>

<style scoped>
.mode-select {
  width: auto;
  min-width: 90px;
}
/* 选择框本体：透明底 + 暗色细线边框 */
.mode-select :deep(.t-input) {
  background: transparent !important;
  box-shadow: none !important;
  border-color: #444 !important;
  border-radius: 6px;
}
.mode-select :deep(.t-input:hover) {
  border-color: #555 !important;
}
.mode-select :deep(.t-input.t-is-focused),
.mode-select :deep(.t-is-focused > .t-input) {
  border-color: #666 !important;
  box-shadow: none !important;
}
/* 内部所有元素统一暗色主题 */
.mode-select :deep(.t-select__wrapper),
.mode-select :deep(.t-select-input),
.mode-select :deep(.t-input__wrap),
.mode-select :deep(.t-input__inner) {
  background: transparent !important;
  box-shadow: none !important;
  color: #eee !important;
  caret-color: #eee;
}
/* 已选项文字 */
.mode-select :deep(.t-select__selected-item) {
  font-size: 11px;
  color: #ddd;
}
/* 下拉箭头 — 淡灰不抢眼 */
.mode-select :deep(.t-select__caret),
.mode-select :deep(.t-input__suffix-icon svg),
.mode-select :deep(.t-input__suffix-icon path),
.mode-select :deep(.t-input__suffix-icon) {
  color: #999 !important;
  fill: currentColor !important;
}
</style>