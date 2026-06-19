<!--
InitWizard：初始化向导

为什么做：首次使用时用户需要配置工作区/模型/API Key，不能直接丢进空白界面。
实现方法：Vue 3 步骤向导（WorkspaceStep → ModelStep → ApiKeyStep），配置完成后启动 Dashboard。
实现效果：首次打开不迷茫，引导式完成初始配置。

技术栈：Vue 3 SFC, Element Plus steps
层&依赖：frontend.presentation → init 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §InitWizard
-->
