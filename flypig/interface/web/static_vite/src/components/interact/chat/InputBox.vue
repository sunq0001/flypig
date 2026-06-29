<!--
InputBox：输入框父容器

组装 ModeSelect + ModelSelect + SendButton + textarea，
未来可在底部插入 FileChips / ApiKeyBadge 等子组件。
-->
<template>
  <div class="input-box">
    <div class="input-container">
      <textarea
        v-model="text"
        rows="1"
        placeholder="输入消息...（拖拽文件、粘贴图片）"
        :disabled="disabled"
        class="native-textarea"
        autofocus
        @keydown.enter.prevent="handleSend"
      />

      <div class="input-footer">
        <ModeSelect v-model="currentMode" @update:model-value="emit('update:mode', $event)" />
        <span class="sep">|</span>
        <ModelSelect v-model="currentModel" :options="models" @update:model-value="emit('update:model', $event)" />
        <span class="spacer" />
        <SendButton :disabled="disabled" :has-text="!!text.trim()" @click="handleSend" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import ModeSelect from '../input/ModeSelect.vue'
import ModelSelect from '../input/ModelSelect.vue'
import SendButton from '../input/SendButton.vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  model: { type: String, default: '' },
  mode: { type: String, default: 'explore' },
  models: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['send', 'update:model', 'update:mode'])

const text = ref(props.modelValue || '')
const currentMode = ref(props.mode)
const currentModel = ref(props.model)

watch(() => props.modelValue, v => text.value = v)
watch(() => props.mode, v => currentMode.value = v)
watch(() => props.model, v => currentModel.value = v)

function handleSend() {
  const msg = text.value.trim()
  if (!msg || props.disabled) return
  emit('send', { text: msg, mode: currentMode.value, model: currentModel.value })
  text.value = ''
}
</script>

<style scoped>
.input-box { flex-shrink: 0; padding: 0 12px 8px; }
.input-container {
  position: relative; background: #252526; border: 1px solid #333;
  border-radius: 10px; overflow: hidden; transition: border-color 0.15s;
}
.input-container:focus-within { border-color: #409eff; }
/* 原生 textarea */
.native-textarea {
  display: block;
  width: 100%;
  box-sizing: border-box;
  background: transparent;
  border: none;
  color: #ccc;
  caret-color: #ccc;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.5;
  padding: 10px 12px 4px;
  min-height: 40px;
  max-height: 120px;
  resize: vertical;
  outline: none;
}
.native-textarea::placeholder { color: #555; }
.native-textarea:focus { outline: none; }
.input-footer {
  display: flex; align-items: center; gap: 6px; padding: 2px 8px 8px;
}
.sep { color: #444; font-size: 11px; user-select: none; }
.spacer { flex: 1; }
</style>
