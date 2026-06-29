<!--
ModeSelect：Explore / Plan / Execute 模式选择下拉

props: modelValue — 当前模式值
emits: update:modelValue
-->
<template>
  <el-select
    class="mode-select"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    size="small"
    popper-class="mode-select-popper"
  >
    <el-option value="explore" label="🔍 Explore" />
    <el-option value="plan" label="📋 Plan" />
    <el-option value="execute" label="⚡ Execute" />
  </el-select>
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
.mode-select :deep(.el-select__wrapper) {
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 4px;
  min-height: 20px;
}
.mode-select :deep(.el-select__selected-item) {
  font-size: 11px;
  color: #888;
}
.mode-select :deep(.el-select__caret) {
  color: #555;
  font-size: 10px;
}
</style>

<style>
.mode-select-popper {
  background: #252526 !important;
  border: 1px solid #333 !important;
  min-width: 100px;
}
.mode-select-popper .el-select-dropdown__item {
  font-size: 12px;
  color: #ccc;
  background: transparent !important;
}
.mode-select-popper .el-select-dropdown__item:hover,
.mode-select-popper .el-select-dropdown__item.hover {
  background: #3c3c3c !important;
}
.mode-select-popper .el-select-dropdown__item.is-selected {
  color: #409eff !important;
}
</style>