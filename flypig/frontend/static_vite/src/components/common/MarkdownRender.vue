<!--
MarkdownRender：Markdown 渲染

为什么做：AI 输出的 Markdown 格式文本需要渲染为富文本（标题/代码块/列表/表格/图片）。
实现方法：marked 解析 Markdown + highlight.js 代码高亮，扩展 code block 渲染器。
实现效果：AI 输出排版美观，代码块有语法高亮。

技术栈：Vue 3 SFC, marked + highlight.js
层&依赖：frontend.presentation → common 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §技术栈
-->
