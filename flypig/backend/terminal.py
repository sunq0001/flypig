"""用户手动 PTY 终端 (WebSocket)

为什么做：用户需要一个独立的手动终端执行交互式命令（vim/python REPL），AI 不注入任何命令到终端。
实现方法：Quart WebSocket 连接 xterm.js，subprocess 创建 PTY 进程。终端输出只读，用户手动操作。
实现效果：AI 不污染用户终端，用户需要手动操作时打开独立 xterm 标签页。
技术栈：Quart WebSocket, xterm.js, 无 AI 注入

层&依赖：backend 层，依赖 subprocess + PTY
细节见文档：docs/docs_refactor/subprocess.md → §用户 PTY、data-flow.md → §终端数据流
"""