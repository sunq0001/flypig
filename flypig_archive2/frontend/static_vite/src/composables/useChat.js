/** useChat：SSE 对话 + tool_call 交互
 * @module useChat
   为什么做：前端需要一行 useChat 代替手写 ReadableStream 解析 SSE 流。
   实现方法：@ai-sdk/vue useChat composable，onToolCall/onResponse/onError 回调处理事件。
   实现效果：流式对话、工具调用、打字机效果原生支持，不需要手动管理状态。
   技术栈：@ai-sdk/vue useChat, onToolCall/onResponse/onError
   层&依赖：frontend.composables → chat 组件群
   细节见文档：docs/docs_refactor/frontend-arch.md → §Vercel AI SDK

   注意事项：
   - 每次发送消息必须带上 model 参数，后端拒绝不传 model 的请求
   - model 值来自 model-bar 当前选中的模型名（从 /api/config 获取），前端不硬编码
   - 发送前检查有无 API Key：无 Key 则弹窗要求输入，不直接发送
   - 初始状态：config / workspace / model / mode 全为 null，GET /api/config 后才赋值 */
