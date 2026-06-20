<!--
ModeSelect：Explore / Plan / Execute 模式选择下拉

props: modelValue — 当前模式值
emits: update:modelValue
-->
<template>
  <select class="mode-select" :value="modelValue" @change="$emit('update:modelValue', $event.target.value)">
    <option value="explore">🔍 Explore</option>
    <option value="plan">📋 Plan</option>
    <option value="execute">⚡ Execute</option>
  </select>
</template>

<script setup>
defineProps({ modelValue: { type: String, default: 'explore' } })
defineEmits(['update:modelValue'])
</script>

<style scoped>
.mode-select {
  background: transparent; color: #888; border: none; outline: none;
  font-size: 11px; cursor: pointer; padding: 2px 0; appearance: auto; max-width: 110px;
}
.mode-select option { background: #2a2a2a; color: #ccc; }
</style>
