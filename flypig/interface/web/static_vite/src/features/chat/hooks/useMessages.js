/** useMessages：消息状态管理
 * @module useMessages
   为什么做：对话消息需要响应式状态管理，按时间/类型/角色组织。
   实现方法：Vue reactive messages 数组 + loading/streaming 状态标志。
   实现效果：消息列表自动更新的前提。
   技术栈：Vue reactive, messages/loading/streaming
   层&依赖：frontend.composables
   细节见文档：docs/docs_refactor/frontend-arch.md → §数据流 */
