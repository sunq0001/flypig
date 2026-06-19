<!--
FileTree：文件树

为什么做：用户需要直观地看到工作区的文件和目录结构。
实现方法：递归组件渲染文件树，按目录/文件分组，支持展开/折叠/图标。通过 useFileTree composable 加载数据。
实现效果：文件结构一目了然，点击文件在编辑器中打开。

技术栈：Vue 3 SFC, 递归组件
层&依赖：frontend.presentation → sidebar 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
