<!--
MessageItem：单条消息渲染

为什么做：用户发送的每一条消息和 AI 回复需要以对话气泡形式展示。
实现方法：根据 role 区分用户/AI 气泡样式，支持 markdown 渲染（暂用纯文本）。
实现效果：用户消息右对齐蓝色气泡，AI 回复左对齐灰色气泡。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → chat 组件群
-->
<template>
  <div class="message-item" :class="[message.role]">
    <div class="avatar">{{ message.role === 'user' ? '🧑' : '🤖' }}</div>
    <div class="bubble">
      <div class="content">{{ message.content || (loading ? '...' : '') }}</div>
      <div class="time">{{ time }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: { type: Object, required: true },
  loading: { type: Boolean, default: false },
})

const time = computed(() => {
  const d = new Date(props.message.id?.split('-')[0] || Date.now())
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})
</script>

<style scoped>
.message-item {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  max-width: 100%;
}
.message-item.user { flex-direction: row-reverse; }
.avatar { flex-shrink: 0; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
.bubble {
  max-width: 75%;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}
.user .bubble { background: #409eff; color: #fff; border-bottom-right-radius: 2px; }
.assistant .bubble { background: #333; color: #ccc; border-bottom-left-radius: 2px; }
.content { white-space: pre-wrap; }
.time { font-size: 10px; color: #888; margin-top: 4px; text-align: right; }
</style>
