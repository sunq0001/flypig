"""subprocess 命令执行工具

为什么做：AI 需要执行 shell 命令（安装依赖/运行测试/查看日志），需要一个受控的 subprocess 入口。
实现方法：subprocess.run 执行命令，超时控制，无 PTY（不注入交互式终端）。结果原样返回 AI。
实现效果：AI 可以在工作区中执行命令并获取输出，不会卡在交互式程序中。
技术栈：subprocess.run, 超时控制, 无 PTY

层&依赖：infrastructure.tools.system 层，依赖 subprocess + sandbox（沙箱降级）
细节见文档：docs/docs_refactor/subprocess.md → §执行策略
"""
