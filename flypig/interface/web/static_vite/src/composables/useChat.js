/** useChat：SSE 对话 + streaming 打字机效果
 *
 * 为什么做：前端需要一行 useChat 代替手写 ReadableStream 解析 SSE 流。
 * 实现方法：@ai-sdk/vue useChat composable，逐 token 追加到 messages 实现打字机效果。
 * 实现效果：AI 回复逐字出现，不是整段一起显示。
 *
 * 注意事项：
 * - 每次发送消息必须带上 model 参数
 * - model 值来自 ModelSelect 当前选中的模型名
 * - 发送前检查有无 API Key：无 Key 则弹窗要求输入
 */

import { useChat as useAIChat } from '@ai-sdk/vue'
import { ref, computed } from 'vue'

export function useChat() {
  const selectedModel = ref('')
  const hasApiKey = ref(false)

  const chat = useAIChat({
    api: '/api/chat',
    headers: { 'Content-Type': 'application/json' },
    body: () => ({
      model: selectedModel.value,
    }),
    onError: (err) => {
      console.error('[useChat] error:', err.message)
    },
    onFinish: () => {
      console.log('[useChat] response complete')
    },
    sendExtraMessageFields: true,
  })

  const sendMessage = async (content) => {
    if (!content.trim()) return
    if (!selectedModel.value) {
      console.warn('[useChat] no model selected')
      return
    }
    chat.append({ role: 'user', content })
  }

  const stopGeneration = () => {
    chat.stop()
  }

  return {
    messages: chat.messages,
    input: chat.input,
    isLoading: chat.isLoading,
    error: chat.error,
    selectedModel,
    hasApiKey,
    sendMessage,
    stopGeneration,
    append: chat.append,
    setInput: (v) => { chat.input.value = v },
    reload: chat.reload,
  }
}
