<!--
MessageList：消息列表

为什么做：展示多轮对话消息，新消息自动滚到底部。
使用 content-visibility 让浏览器自动跳过不可见消息的渲染。
-->

<template>
  <div ref="scrollRef" class="message-list">
    <div v-if="!messages.length" class="empty">开始一段新对话</div>
    <MessageItem
      v-for="m in messages" :key="m.id"
      :message="m"
      :loading="loading && m === messages[messages.length - 1] && m.role === 'assistant'"
    />
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import MessageItem from './MessageItem.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const scrollRef = ref(null)

// ── 获取消息文本内容（兼容 content 和 parts 格式） ──
function getMessageContent(msg) {
  if (!msg) return ''
  if (msg.content) return msg.content
  if (msg.parts?.length) return msg.parts.filter(p => p.type === 'text').map(p => p.text).join('')
  return ''
}

// ── 打字机效果诊断: 记录每次内容变化（精确到毫秒） ──
let lastLen = 0
watch(() => {
  const last = props.messages[props.messages.length - 1]
  return last?.role === 'assistant' ? getMessageContent(last) : ''
}, (val) => {
  const now = Date.now()
  const ts = new Date(now).toISOString().slice(11, 23)
  if (val && val.length !== lastLen) {
    const added = val.length - lastLen
    console.log(`[fe] ${ts} +${added} total=${val.length} "${val.slice(-30)}"`)
    lastLen = val.length
  } else if (!val && lastLen !== 0) {
    console.log(`[fe] ${ts} RESET (content cleared)`)
    lastLen = 0
  }
  // 始终打印最新消息的 metadata
  const last = props.messages[props.messages.length - 1]
  if (last?.role === 'assistant') {
    const ml = props.messages.length
    console.log(`[fe] ${ts} msgs=${ml} role=${last.role} id=${last.id?.slice(0,8)||'-'} parts=${last.parts?.length||0}`)
  }
})

watch(() => props.messages.length, async () => {
  lastLen = 0  // 新消息重置计数
  await nextTick()
  if (scrollRef.value) {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  }
})
</script>

<style scoped>
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}
.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #555;
  font-size: 14px;
}
:deep(.message-item) {
  content-visibility: auto;
  contain-intrinsic-size: 60px;
}
</style>
