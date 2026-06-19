/* main：Vue app 挂载点
   为什么做：浏览器加载 index.html 后需要创建 Vue 实例并挂载到 #app 容器。
   实现方法：Vue 3 createApp + mount，注册 Element Plus 插件 + useChat composable。
   实现效果：Vue 应用启动，所有组件可正常渲染。
   技术栈：Vue 3 createApp + mount, Element Plus 注册
   层&依赖：frontend.presentation（入口点）
   细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构 */
