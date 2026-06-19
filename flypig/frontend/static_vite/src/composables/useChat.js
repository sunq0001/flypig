/* useChat：SSE 对话 + tool_call 交互
   为什么做：前端需要一行 useChat 代替手写 ReadableStream 解析 SSE 流。
   实现方法：@ai-sdk/vue useChat composable，onToolCall/onResponse/onError 回调处理事件。
   实现效果：流式对话、工具调用、打字机效果原生支持，不需要手动管理状态。
   技术栈：@ai-sdk/vue useChat, onToolCall/onResponse/onError
   层&依赖：frontend.composables → chat 组件群
   细节见文档：docs/docs_refactor/frontend-arch.md → §Vercel AI SDK */
