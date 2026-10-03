/** useFileTree：文件树状态
 * @module useFileTree
   为什么做：侧边栏文件树需要加载/展开/选中等状态管理。
   实现方法：fetch /api/tree 加载文件树，响应式管理展开状态和选中文件。
   实现效果：文件树自动同步工作区变化。
   技术栈：fetch /api/tree, 展开/选中
   层&依赖：frontend.composables → sidebar 组件群
   细节见文档：docs/docs_refactor/frontend-arch.md → §侧边栏 */
