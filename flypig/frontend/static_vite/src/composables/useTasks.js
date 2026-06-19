/* useTasks：任务看板状态
   为什么做：任务看板（TaskBoard）需要加载/过滤/排序任务列表。
   实现方法：fetch /api/tasks 加载任务列表，响应式管理状态过滤和排序条件。
   实现效果：任务看板实时同步 AI 创建的任务变更。
   技术栈：fetch /api/tasks, 状态过滤/排序
   层&依赖：frontend.composables → sidebar 组件群
   细节见文档：docs/docs_refactor/mem_convStore_tasks.md → §CRUD */
