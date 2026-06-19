<!--
XtermViewer：xterm 终端实现

为什么做：用户手动终端的核心——基于 xterm.js 的 WebSocket 终端。
实现方法：xterm.js + addon-fit + addon-web-links，通过 WebSocket 连接后端 PTY。
实现效果：终端操作实时同步，双向通信。

技术栈：Vue 3 SFC, xterm.js, WebSocket, addon-fit
层&依赖：frontend.presentation → terminal 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §技术栈
-->
