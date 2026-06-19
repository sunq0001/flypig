<!--
ModelStep：模型选择步骤

为什么做：InitWizard 的第二步——用户选择 AI 模型后端。
实现方法：模型列表展示（DeepSeek/Claude/GPT 等）+ 温度滑块配置。
实现效果：用户选择偏好的 AI 模型和生成风格。

技术栈：Vue 3 SFC, Element Plus select/slider
层&依赖：frontend.presentation → init 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §InitWizard
-->
