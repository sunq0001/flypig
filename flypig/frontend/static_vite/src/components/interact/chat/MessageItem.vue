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
      <div class="content">{{ displayText || (loading ? '...' : '') }}</div>
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

// AI SDK v4+ 使用 parts 格式，兼容老版 content 字段
const displayText = computed(() => {
  const m = props.message
  if (m.parts?.length) {
    return m.parts
      .filter(p => p.type === 'text')
      .map(p => p.text)
      .join('')
  }
  return m.content || ''
})

const time = computed(() => {
  const d = new Date(Date.now())
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})
</script>

<style scoped>
.message-item {
  display: flex;
  gap: 8px;
  padding: 4px 12px;
  max-width: 100%;
}
.message-item.user { flex-direction: row-reverse; }
.avatar { flex-shrink: 0; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 15px; opacity: 0.8; }
.bubble {
  max-width: 75%;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}
/* user: 比背景稍亮，不刺眼 */
.user .bubble {
  background: #2b2b2b;
  color: #d4d4d4;
  border: 1px solid #3c3c3c;
  border-bottom-right-radius: 2px;
}
/* assistant: 和背景一致但有左边框 */
.assistant .bubble {
  background: #1e1e1e;
  color: #d4d4d4;
  border: 1px solid #333;
  border-bottom-left-radius: 2px;
}
.content { white-space: pre-wrap; }
.time { font-size: 10px; color: #555; margin-top: 2px; text-align: right; }
</style>
