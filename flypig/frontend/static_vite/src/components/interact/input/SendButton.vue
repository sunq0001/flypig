<!--
SendButton：发送 ↗ / 停止 ■

为什么做：空闲时发消息，AI 生成中停止输出。
实现方法：disabled=false 显示 ↗，disabled=true 显示 ■。
  无文字时灰色禁用，有文字时蓝色激活。
-->
<template>
  <button
    class="send-btn"
    :class="{ active: !disabled && hasText, stop: disabled }"
    :disabled="!disabled && !hasText"
    @click="$emit('click')"
  >
    <svg v-if="!disabled" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
    </svg>
    <svg v-else width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="2"/>
    </svg>
  </button>
</template>

<script setup>
defineProps({ disabled: Boolean, hasText: Boolean })
defineEmits(['click'])
</script>

<style scoped>
.send-btn {
  width: 22px; height: 22px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: #555;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  flex-shrink: 0;
  transition: all 0.15s;
}
.send-btn.active { color: #409eff; }
.send-btn.stop { color: #f56c6c; }
.send-btn.stop:hover { background: rgba(245,108,108,0.15); }
.send-btn:hover:not(:disabled):not(.stop) { background: #333; }
</style>
