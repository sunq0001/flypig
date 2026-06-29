/** sfc-compiler：Vue SFC 编译器
 * @module sfc-compiler
   为什么做：LivePreview 需要实时编译用户/AI 写的 Vue 单文件组件为可渲染内容。
   实现方法：@vue/compiler-sfc 编译 SFC → 动态创建组件实例 → 挂载到预览区域。
   实现效果：用户实时看到组件渲染效果。
   技术栈：@vue/compiler-sfc, 实时编译渲染
   层&依赖：frontend.lib
   细节见文档：docs/docs_refactor/frontend-arch.md → §LivePreview */
