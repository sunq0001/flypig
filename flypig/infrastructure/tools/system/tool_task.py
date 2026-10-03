"""后台任务管理工具

为什么做：AI 启动的长时间运行命令（编译/测试/部署）需要后台执行和管理，不能阻塞对话。
实现方法：subprocess.Popen 启动后台进程 + 自研环形缓冲区存储输出。提供 task_status/task_list/task_log。
实现效果：AI 可以在后台执行命令，同时继续对话。用户随时查看后台任务状态和日志。
技术栈：subprocess.Popen, 环形缓冲区, task_status/task_list/task_log

层&依赖：infrastructure.tools.system 层，依赖 subprocess + ProcessManager
细节见文档：docs/docs_refactor/tech-stack.md → §后台任务
"""

# TODO: 骨架文件占位，待具体实现
