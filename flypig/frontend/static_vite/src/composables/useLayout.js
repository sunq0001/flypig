/* useLayout：布局状态
   为什么做：三栏布局的分栏宽度、侧边栏开关、面板切换需要响应式管理。
   实现方法：Vue reactive 管理各面板宽度/可见性，支持拖动调整。
   实现效果：用户可自定义界面布局。
   技术栈：Vue reactive, 分栏宽度/侧边栏开关
   层&依赖：frontend.composables → layout 组件群
   细节见文档：docs/docs_refactor/frontend-arch.md → §布局 */
