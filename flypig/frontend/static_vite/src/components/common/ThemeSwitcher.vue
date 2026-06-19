<!--
ThemeSwitcher：主题切换

为什么做：用户偏好不同的界面主题（默认/赛博朋克/可爱），需要一键切换。
实现方法：切换全局 CSS 变量文件，通过 useTheme composable 持久化到 localStorage。
实现效果：用户选择喜欢的主题，下次打开自动恢复。

技术栈：Vue 3 SFC, CSS 变量切换
层&依赖：frontend.presentation → common 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §主题切换
-->
