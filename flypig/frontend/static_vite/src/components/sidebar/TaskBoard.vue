<!--
TaskBoard：任务看板面板

为什么做：用户需要一个看板视图来管理 AI 创建的所有任务，跟踪进度和状态。
实现方法：Element Plus table/kanban 渲染任务列表，按状态分组（pending/in_progress/completed/cancelled）。支持搜索/过滤。
实现效果：任务管理清晰，AI 拆解的任务不会漏掉。

技术栈：Vue 3 SFC, Element Plus table/kanban, fetch /api/tasks
层&依赖：frontend.presentation → sidebar 组件群
细节见文档：docs/docs_refactor/mem_convStore_tasks.md → §任务状态
-->
