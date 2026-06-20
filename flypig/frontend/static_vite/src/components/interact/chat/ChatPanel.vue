<!--
ChatPanel：对话框面板容器

为什么做：用户与 AI 对话的整个界面，组合 InputBox + MessageList。
实现方法：管理 messages + 当前 mode/model 状态，SSE 流式请求 /api/chat。
实现效果：输入框带 mode/模型选择，AI 回复流式出现。

技术栈：Vue 3 SFC, Element Plus, ReadableStream SSE
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/api-reference.md → §SSE 事件格式
-->
<template>
  <div class="chat-panel">
    <MessageList :messages="messages" :loading="loading" />
    <InputBox
      :model="currentModel"
      :models="modelList"
      :mode="currentMode"
      :disabled="loading"
      @send="onSend"
      @update:model="m => currentModel = m"
      @update:mode="m => currentMode = m"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import MessageList from './MessageList.vue'
import InputBox from './InputBox.vue'

const props = defineProps({
  model: { type: String, default: '' },
})

const currentModel = ref(props.model)
const currentMode = ref('explore')
const modelList = ref([])  // 后续从 /api/config 获取

const messages = ref([])
const loading = ref(false)

async function onSend({ text, mode, model }) {
  messages.value.push({ role: 'user', content: text, id: Date.now() + '-user' })
  loading.value = true

  const assistantId = Date.now() + '-assistant'
  messages.value.push({ role: 'assistant', content: '', id: assistantId })

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: messages.value.filter(m => m.content).map(m => ({ role: m.role, content: m.content })),
        model: model || undefined,
        mode: mode || undefined,
      }),
    })

    if (!res.ok) {
      setMessage(assistantId, `请求失败 (${res.status})`)
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') continue
          try {
            const parsed = JSON.parse(data)
            const delta = parsed.choices?.[0]?.delta?.content
            if (delta) appendContent(assistantId, delta)
          } catch { /* */ }
        }
      }
    }
  } catch (e) {
    setMessage(assistantId, `网络错误: ${e.message}`)
  } finally {
    loading.value = false
  }
}

function appendContent(id, delta) {
  const m = messages.value.find(m => m.id === id)
  if (m) m.content += delta
}

function setMessage(id, content) {
  const m = messages.value.find(m => m.id === id)
  if (m) m.content = content
}
</script>

<style scoped>
.chat-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
}
</style>
