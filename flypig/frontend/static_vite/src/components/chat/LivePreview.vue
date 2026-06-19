<!--
LivePreview：实时预览

为什么做：AI 生成的 HTML/组件/UI 需要实时渲染看效果，不是看代码本身。
实现方法：iframe / @vue/compiler-sfc 实时编译渲染。
实现效果：AI 说"加个按钮"，用户立刻看到按钮长什么样。

技术栈：Vue 3 SFC, @vue/compiler-sfc, iframe
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §反馈即预览
-->
