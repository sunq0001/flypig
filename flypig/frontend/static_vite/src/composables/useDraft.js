/* useDraft：草稿管理
   为什么做：用户在输入框中的草稿（写了但没发送的内容）需要临时保存，不会因切换会话丢失。
   实现方法：localStorage 按 session_id 保存/恢复输入草稿。
   实现效果：切换会话回来草稿还在，不丢输入。
   技术栈：localStorage, 输入框草稿恢复
   层&依赖：frontend.composables → chat 组件群
   细节见文档：docs/docs_refactor/chat-ux.md → §输入框 */
