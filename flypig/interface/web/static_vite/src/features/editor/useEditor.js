/** useEditor：编辑器状态
 * @module useEditor
   为什么做：Monaco Editor 的打开文件/编辑内容/标签页切换需要状态管理。
   实现方法：Vue reactive 管理打开的文件列表、当前选中文件、文件内容。
   实现效果：编辑器状态与文件操作联动。
   技术栈：Monaco Editor, 文件打开/编辑
   层&依赖：frontend.composables → editor 组件群
   细节见文档：docs/docs_refactor/frontend-arch.md → §编辑器 */
