<!-- MessageItem：单条消息气泡，支持流式打字机效果 -->
<template>
  <div
    class="message-item"
    :class="[message.role]"
  >
    <div class="avatar">
      {{ message.role === 'user' ? '🧑' : '🤖' }}
    </div>
    <div class="bubble">
      <div class="content">
        {{ displayText }}
      </div>
      <div class="time">
        {{ time }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  message: { type: Object, required: true },
  loading: { type: Boolean, default: false },
})

function getFullText(m) {
  if (!m) return ''
  if (m.content) return m.content
  if (m.parts?.length) return m.parts.filter(p => p.type === 'text').map(p => p.text).join('')
  return ''
}

const isUser = computed(() => props.message.role === 'user')
const displayText = ref('')

// 立即显示已有文本（历史消息或用户消息）
const initial = getFullText(props.message)
if (initial || isUser.value) displayText.value = initial

// 流式进行中：100ms 轮询检测新文本
let dataTimer = null
if (props.loading && !isUser.value) {
  let lastKnown = initial
  dataTimer = setInterval(() => {
    const cur = getFullText(props.message)
    if (cur.length > lastKnown.length) {
      displayText.value = cur
      lastKnown = cur
    }
  }, 100)
}

// 流式结束 → 停止轮询
watch(() => props.loading, (v) => {
  if (!v && dataTimer) {
    clearInterval(dataTimer)
    dataTimer = null
    // 确保最终内容显示
    const final = getFullText(props.message)
    if (final) displayText.value = final
  }
})

onBeforeUnmount(() => {
  if (dataTimer) clearInterval(dataTimer)
})

const time = computed(() => {
  const d = new Date()
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})
</script>

<style scoped>
.message-item { display: flex; gap: 8px; padding: 4px 12px; max-width: 100%; content-visibility: auto; contain-intrinsic-size: 60px; }
.message-item.user { flex-direction: row-reverse; }
.avatar { flex-shrink: 0; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 15px; opacity: 0.8; }
.bubble { max-width: 75%; padding: 6px 10px; border-radius: 6px; font-size: 13px; line-height: 1.5; word-break: break-word; }
.user .bubble { background: #2b2b2b; color: #d4d4d4; border: 1px solid #3c3c3c; border-bottom-right-radius: 2px; }
.assistant .bubble { background: #1e1e1e; color: #d4d4d4; border: 1px solid #333; border-bottom-left-radius: 2px; }
.content { white-space: pre-wrap; }
.time { font-size: 10px; color: #555; margin-top: 2px; text-align: right; }
</style>
