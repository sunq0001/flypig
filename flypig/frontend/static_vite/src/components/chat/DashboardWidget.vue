<!--
DashboardWidget：仪表盘小部件

为什么做：Dashboard 首页需要显示用量/任务/回顾等概览信息。
实现方法：Vue 3 渲染卡片式小部件，按类型（用量/任务/回顾）分发数据。
实现效果：用户一打开就看到整体状态，不需要手动查询。

技术栈：Vue 3 SFC, Element Plus card
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §Dashboard
-->
