<!--
ChatPanel：对话框面板容器

为什么做：用户与 AI 对话的整个界面，组合 InputBox + MessageList。
实现方法：useChat(@ai-sdk/vue) 管理消息/流式/SSE，InputBox 发送事件桥接到 sendMessage。

实现效果：打字机效果由 useChat 原生逐 token 渲染，不再需要手写 ReadableStream。

技术栈：Vue 3 SFC, @ai-sdk/vue useChat

层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/api-reference.md → §SSE 事件格式
-->
<template>
  <div class="chat-panel">
    <MessageList :messages="messages" :loading="isStreaming" />
    <InputBox
      :model="currentModel"
      :models="modelList"
      :mode="currentMode"
      :disabled="isStreaming"
      @send="onSend"
      @update:model="onModelChange"
      @update:mode="m => currentMode = m"
    />

    <!-- API Key 弹框 -->
    <t-dialog
      v-model="showApiKeyDialog"
      title="配置 API Key"
      width="420px"
      :close-on-overlay-click="false"
      :show-close="false"
    >
      <p style="margin-bottom:12px;color:#606266;font-size:13px;">
        模型 <strong>{{ currentModel }}</strong> 尚未配置 API Key。输入后即可开始对话。
      </p>
      <t-input
        v-model="apiKeyInput"
        type="password"
        show-password-icon
        :placeholder="`输入 ${apiKeyProvider} API Key`"
        clearable
      />
      <template #footer>
        <t-button @click="showApiKeyDialog = false">取消</t-button>
        <t-button theme="primary" :disabled="!apiKeyInput.trim()" :loading="savingKey" @click="saveApiKey">
          保存并发送
        </t-button>
      </template>
    </t-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useChat } from '@ai-sdk/vue'
import { useConfigStore } from '../../../stores/config'
import MessageList from './MessageList.vue'
import InputBox from './InputBox.vue'

const props = defineProps({
  model: { type: String, default: '' },
})

const configStore = useConfigStore()

const modelList = computed(() => configStore.models)
const currentModel = ref(props.model || configStore.default_model || '')
const currentMode = ref('explore')

watch(() => configStore.default_model, (val) => {
  if (val && !currentModel.value) {
    currentModel.value = val
  }
}, { immediate: true })

// ── useChat ──
const { messages, status, sendMessage, error } = useChat({
  api: '/api/chat',
  experimental_throttle: 30,
  onError: (e) => console.error('Chat error:', e),
})

const isStreaming = computed(() =>
  status.value === 'submitted' || status.value === 'streaming'
)

// ── 固定间隔轮询 ──
// useChat 内部改数不改引用，Vue 检测不到
// 每 200ms 浅拷贝一次数组，下游才能收到更新
let forcePoll = null
watch(isStreaming, (v) => {
  if (v) {
    const poll = () => {
      messages.value = messages.value.map(m => ({...m}))
    }
    poll()
    forcePoll = setInterval(poll, 200)
  } else {
    if (forcePoll) { clearInterval(forcePoll); forcePoll = null }
  }
})

// ── 模型切换同步到后端 ──
async function onModelChange(m) {
  currentModel.value = m
  try {
    await fetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ default_model: m }),
    })
  } catch { /* */ }
}

// ── API Key ──
const showApiKeyDialog = ref(false)
const apiKeyInput = ref('')
const savingKey = ref(false)
let pendingText = ''

const apiKeyProvider = computed(() => {
  const models = configStore.models || []
  const m = models.find(m => m.name === currentModel.value)
  return m ? m.provider : ''
})

function modelHasKey(modelName) {
  const models = configStore.models || []
  const m = models.find(m => m.name === modelName)
  return m ? m.has_key : false
}

// ── 发送 ──
async function onSend({ text, mode, model }) {
  const actualModel = model || configStore.default_model
  if (!actualModel) return

  // 检查 API Key
  if (!modelHasKey(actualModel)) {
    pendingText = text
    showApiKeyDialog.value = true
    apiKeyInput.value = ''
    return
  }

  currentMode.value = mode

  await sendMessage(
    { text },
    { body: { model: actualModel, mode: mode || 'explore' } }
  )
}

async function saveApiKey() {
  const key = apiKeyInput.value.trim()
  if (!key) return
  savingKey.value = true
  try {
    await fetch('/api/config/apikey', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: apiKeyProvider.value, api_key: key }),
    })
    await configStore.fetchConfig()
    showApiKeyDialog.value = false
    if (pendingText) {
      await onSend({ text: pendingText, mode: currentMode.value, model: currentModel.value })
      pendingText = ''
    }
  } catch { /* */ } finally {
    savingKey.value = false
  }
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

<style>
/* 消息列表滚动条 */
.message-list::-webkit-scrollbar { width: 6px; }
.message-list::-webkit-scrollbar-track { background: transparent; }
.message-list::-webkit-scrollbar-thumb { background: #3c3c3c; border-radius: 3px; }
</style>
