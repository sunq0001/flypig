/* useAchievements：成就系统 (P1)
   为什么做：用户使用 FlyPig 时达成某些里程碑（首次聊天/首次调工具/聊了 100 轮），弹出成就提示增添趣味。
   实现方法：Vue 监听用户事件→检测成就条件→弹出勋章。
   实现效果：使用 FlyPig 有游戏化体验。
   技术栈：Vue, 勋章/成就弹窗
   层&依赖：frontend.composables（P1 预留）
   细节见文档：docs/docs_refactor/chat-ux.md → §情感设计 */
