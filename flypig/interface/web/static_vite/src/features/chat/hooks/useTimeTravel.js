/** useTimeTravel：时间旅行 (P1)
 * @module useTimeTravel
   为什么做：用户需要回溯任意历史 turn 时的完整状态（消息/文件/任务）。
   实现方法：fetch 历史会话数据 + 对应 turn 的任务快照 + checkout 文件状态。
   实现效果：用户"回到过去"查看某轮对话时的工作区全貌。
   技术栈：Vue, 回溯历史状态
   层&依赖：frontend.composables（P1 预留）
   细节见文档：docs/docs_refactor/chat-ux.md → §时间旅行 */
