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
    <MessageList
      :messages="messages"
      :loading="isStreaming"
    />
    <InputBox
      :model="currentModel"
      :models="modelList"
      :mode="currentMode"
      :disabled="isStreaming"
      @send="onSend"
      @update:model="onModelChange"
      @update:mode="m => currentMode = m"
    />

    <!-- API Key 弹框（自定义 div 弹窗，避免 TDesign Dialog Teleport bug） -->
    <div
      v-if="showApiKeyDialog"
      class="ak-overlay"
      @click.self="showApiKeyDialog = false"
    >
      <div class="ak-box">
        <div class="ak-header">
          <span>配置 API Key</span>
          <button
            class="ak-close"
            @click="showApiKeyDialog = false"
          >
            ✕
          </button>
        </div>
        <div class="ak-body">
          <p class="ak-desc">
            模型 <strong>{{ currentModel }}</strong> 尚未配置 API Key。输入后即可开始对话。
          </p>
          <t-input
            v-model="apiKeyInput"
            type="password"
            show-password-icon
            :placeholder="`输入 ${apiKeyProvider} API Key`"
            clearable
          />
        </div>
        <div class="ak-footer">
          <t-button @click="showApiKeyDialog = false">
            取消
          </t-button>
          <t-button
            theme="primary"
            :disabled="!apiKeyInput.trim()"
            :loading="savingKey"
            @click="saveApiKey"
          >
            保存并发送
          </t-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useChat } from '@ai-sdk/vue'
import { useConfigStore } from '@/stores/config'
import { updateDefaultModel, saveApiKey as saveApiKey_ } from '@/utils/api'
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
const { messages, status, sendMessage } = useChat({
  api: '/api/chat',
  experimental_throttle: 30,  // ms, 流式更新节流间隔
  onError: () => {}, // 由外层 useChat 的 error 返回值处理
})

const isStreaming = computed(() =>
  status.value === 'submitted' || status.value === 'streaming'
)

// ── 固定间隔轮询 ──
// useChat 内部改数不改引用（shallowRef + in-place mutation），Vue 检测不到
// 每 200ms 浅拷贝一次数组，下游才能收到更新
let forcePoll = null
watch(isStreaming, (v) => {
  if (v) {
    const poll = () => {
      messages.value = messages.value.map(m => ({...m}))
    }
    poll()
    forcePoll = setInterval(poll, 200)
  } else if (forcePoll) {
    // 流结束前再做最后一次拷贝，避免遗漏最后 200ms 内的内容
    messages.value = messages.value.map(m => ({...m}))
    clearInterval(forcePoll)
    forcePoll = null
  }
})

// ── 模型切换同步到后端 ──
async function onModelChange(m) {
  currentModel.value = m
  try {
    await updateDefaultModel(m)
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
    await saveApiKey_(apiKeyProvider.value, key)
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
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
  overflow: hidden;
}
</style>

<style>
/* 消息列表滚动条 */
.message-list::-webkit-scrollbar { width: 6px; }
.message-list::-webkit-scrollbar-track { background: transparent; }
.message-list::-webkit-scrollbar-thumb { background: #3c3c3c; border-radius: 3px; }

/* API Key 弹窗 */
.ak-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
}
.ak-box {
  background: #252526;
  border: 1px solid #333;
  border-radius: 8px;
  width: 420px;
  max-width: 90vw;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.ak-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid #333;
  color: #ccc;
  font-size: 14px;
  font-weight: 500;
}
.ak-close {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  font-size: 16px;
  padding: 2px 6px;
  border-radius: 3px;
}
.ak-close:hover {
  color: #ccc;
  background: #333;
}
.ak-body {
  padding: 20px;
}
.ak-desc {
  margin-bottom: 12px;
  color: #999;
  font-size: 13px;
  line-height: 1.5;
}
.ak-desc strong {
  color: #ccc;
}
.ak-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding: 12px 20px;
  border-top: 1px solid #333;
}
</style>
