/* useMarkdownRender：Markdown 渲染扩展
   为什么做：默认 marked 渲染不够定制化，需要扩展（自定义代码块/卡片/图表渲染器）。
   实现方法：marked extension 自定义渲染器 + highlight.js 代码高亮。
   实现效果：Markdown 渲染支持 FlyPig 特有卡片和交互组件。
   技术栈：marked extension, 自定义渲染
   层&依赖：frontend.composables → common 组件群
   细节见文档：docs/docs_refactor/frontend-arch.md → §Markdown */
