/** useFileDrop：文件拖拽
 * @module useFileDrop
   为什么做：用户拖文件到输入框时需要预览缩略图并上传到后端。
   实现方法：监听 drag/drop 事件，生成缩略图预览，调用 /api/upload 上传。
   实现效果：拖文件进输入框即上传，操作直觉化。
   技术栈：拖入输入框, 缩略图预览/上传
   层&依赖：frontend.composables → chat 组件群
   细节见文档：docs/docs_refactor/chat-ux.md → §输入框 */
