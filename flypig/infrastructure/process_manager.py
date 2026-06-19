"""后台进程管理器

为什么做：AI 启动的后台任务（编译/测试）需要进程生命周期管理，包括清理和状态查询。
实现方法：subprocess.Popen 管理子进程，提供 start/stop/status/log 接口。tool_task / /api/agent/stop 共用。
实现效果：后台任务不会成为僵尸进程，可通过前端或 API 随时停止。
技术栈：subprocess.Popen, 生命周期/清理/状态查询

层&依赖：infrastructure 层，依赖 subprocess
细节见文档：docs/docs_refactor/tech-stack.md → §后台任务
"""