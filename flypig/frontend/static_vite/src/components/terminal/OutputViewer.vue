<!--
OutputViewer：只读输出查看器

为什么做：AI 执行的命令输出需要以只读形式展示在终端标签页中，用户不能交互。
实现方法：Vue 3 渲染命令输出文本，滚动浏览。
实现效果：AI 命令输出可查看，用户不会误操作。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → terminal 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §终端面板
-->
