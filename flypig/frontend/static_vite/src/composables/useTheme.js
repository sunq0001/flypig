/* useTheme：主题切换状态
   为什么做：用户选择的主题（默认/赛博朋克/可爱）需要持久化到 localStorage。
   实现方法：切换 CSS 变量文件，localStorage 持久化选择。
   实现效果：用户打开页面自动恢复上次选的主题。
   技术栈：CSS 变量, localStorage 持久化
   层&依赖：frontend.composables → common 组件群
   细节见文档：docs/docs_refactor/chat-ux.md → §主题切换 */
