/* useTerminal：终端 WebSocket
   为什么做：前端需要连接后端 PTY WebSocket，将终端 I/O 桥接到 xterm.js。
   实现方法：WebSocket 连接 /api/terminal，发送用户输入、接收终端输出。
   实现效果：终端实时交互，用户手动操作。
   技术栈：WebSocket, xterm.js 集成
   层&依赖：frontend.composables → terminal 组件群
   细节见文档：docs/docs_refactor/frontend-arch.md → §终端面板 */
