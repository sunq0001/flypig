<!--
ModelSelect：模型选择下拉

props: modelValue — 当前模型, options — 模型列表
emits: update:modelValue
-->
<template>
  <select class="model-select" :value="modelValue" @change="$emit('update:modelValue', $event.target.value)">
    <option value="" disabled>模型</option>
    <option v-for="m in options" :key="m" :value="m">{{ m }}</option>
  </select>
</template>

<script setup>
defineProps({ modelValue: { type: String, default: '' }, options: { type: Array, default: () => [] } })
defineEmits(['update:modelValue'])
</script>

<style scoped>
.model-select {
  background: transparent; color: #888; border: none; outline: none;
  font-size: 11px; cursor: pointer; padding: 2px 0; appearance: auto; max-width: 120px;
}
.model-select option { background: #2a2a2a; color: #ccc; }
</style>
