<!--
TaskHistoryDialog：任务历史弹窗

为什么做：用户需要查看单个任务的状态变更历史——什么时候创建、什么时候完成、中途变更了什么。
实现方法：Element Plus dialog 渲染按时间线排列的状态变更记录。
实现效果：任务的状态流转一目了然。

技术栈：Vue 3 SFC, Element Plus dialog/timeline
层&依赖：frontend.presentation → common 组件群
细节见文档：docs/docs_refactor/mem_convStore_tasks.md → §任务状态
-->
