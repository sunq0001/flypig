<!--
CodeExecBlock：代码执行块

为什么做：AI 生成的代码片段需要直接在对话中执行并展示结果，用户不用手动复制到终端。
实现方法：发送到后端 subprocess 执行 → 返回 stdout/stderr/exit_code → 渲染在代码块下方。
实现效果：AI 给出代码→直接看效果→修改→再看效果，循环不离开对话框。

技术栈：Vue 3 SFC, subprocess stdout/stderr, WebSocket
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/chat-ux.md → §代码执行
-->
