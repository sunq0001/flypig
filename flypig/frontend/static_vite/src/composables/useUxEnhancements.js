/* useUxEnhancements：UX 增强
   为什么做：打字机效果/焦点跟随/情绪价值等细节体验优化，放在一个 composable 集中管理。
   实现方法：打字机逐字渲染、消息自动聚焦、错误时的安抚动画。
   实现效果：对话体验流畅有温度。
   技术栈：打字机/焦点/情绪价值
   层&依赖：frontend.composables → 全局 UX
   细节见文档：docs/docs_refactor/chat-ux.md → §情感设计 */
