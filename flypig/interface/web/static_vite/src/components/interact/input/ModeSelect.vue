<!--
ModeSelect：Explore / Plan / Execute 模式选择下拉

props: modelValue — 当前模式值
emits: update:modelValue
-->
<template>
  <t-select
    class="mode-select"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    size="small"
    :popup-props="{ overlayClassName: 'mode-select-popper' }"
  >
    <t-option value="explore" label="🔍 Explore" />
    <t-option value="plan" label="📋 Plan" />
    <t-option value="execute" label="⚡ Execute" />
  </t-select>
</template>

<script setup>
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

<style>
.mode-select-popper {
  background: #252526 !important;
  border: 1px solid #333 !important;
  min-width: 100px;
  /* 覆盖 TDesign 浅色主题变量为暗色 */
  --td-bg-color-container: #252526;
  --td-bg-color-container-hover: #3c3c3c;
  --td-bg-color-container-active: #2a2a2a;
  --td-text-color-primary: #e5e5e5;
  --td-text-color-secondary: #999;
  --td-component-stroke: #444;
  --td-border-level-1-color: #444;
}
.mode-select-popper,
.mode-select-popper .t-popup__content {
  background: #252526 !important;
}
.mode-select-popper .t-select-dropdown__item {
  font-size: 12px;
  color: #e5e5e5 !important;
  background: transparent !important;
}
.mode-select-popper .t-select-dropdown__item:hover,
.mode-select-popper .t-select-dropdown__item.hover {
  background: #3c3c3c !important;
}
.mode-select-popper .t-select-dropdown__item.is-selected,
.mode-select-popper .t-option.t-is-selected,
.mode-select-popper .t-select-option.t-is-selected {
  color: #409eff !important;
  background: #2a2a2a !important;
}
</style>