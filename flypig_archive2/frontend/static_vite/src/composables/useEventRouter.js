/** useEventRouter：事件路由分发
 * @module useEventRouter
   为什么做：SSE 事件需要分发给对应的前端组件（token→MessageList, choice→ChoiceCard, tool_call→ToolCallCard）。
   实现方法：按 event.type 路由到对应的处理函数，分发到响应式状态。
   实现效果：SSE 事件自动路由到正确的渲染组件。
   技术栈：SSE 事件→组件分发
   层&依赖：frontend.composables → 全局事件总线
   细节见文档：docs/docs_refactor/api-reference.md → §SSE 事件格式 */
