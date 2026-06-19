<!--
InputBox：输入框

为什么做：用户输入消息、拖拽文件、唤起命令面板的统一入口。
实现方法：Element Plus input 增强，支持文件拖拽缩略图预览、Ctrl+K 命令面板。通过 useChat.handleSubmit 发送。
实现效果：打字不是唯一交互方式，拖文件/点卡片均可触达。

技术栈：Vue 3 SFC, Element Plus input, vue-draggable-next, FileDrop
层&依赖：frontend.presentation → chat 组件群 + composables/useFileDrop.js
细节见文档：docs/docs_refactor/chat-ux.md → §输入框

注意事项：
- 输入框上方有 model-bar（模型下拉 + ⚙ API Key 弹窗图标）
- model-bar 显示的模型名来自 /api/config 返回的 default_model，前端不假设
- 点击发送时 useChat 必须带上 model 参数
- 无 API Key 时点发送弹窗要求输入，不直接发送
-->
