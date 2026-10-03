/** useCommandPalette：命令面板状态
 * @module useCommandPalette
   为什么做：Ctrl+K 命令面板需要搜索/选择/执行命令的状态管理。
   实现方法：监听 Ctrl+K 键盘事件，显示命令列表覆盖层，回车执行选中命令。
   实现效果：键盘快捷键快速操作。
   技术栈：Ctrl+K, 命令搜索/执行
   层&依赖：frontend.composables → common 组件群
   细节见文档：docs/docs_refactor/chat-ux.md → §Command Palette */
