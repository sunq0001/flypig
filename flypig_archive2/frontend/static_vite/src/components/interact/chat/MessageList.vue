<!--
MessageList：消息列表

为什么做：展示多轮对话消息，新消息自动滚到底部。
实现方法：v-for 渲染 MessageItem，watch 消息变化自动 scroll 到底部。
实现效果：消息追加时自动滚动，用户向上翻页时不抢滚动。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → chat 组件群
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

watch(() => props.messages.length, async () => {
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
</style>
