"""Loguru 日志初始化

为什么做：开发和生产环境需要一致的日志格式和级别控制，print 无法满足文件轮转、异步写入、彩色输出等需求。
实现方法：Loguru 一行初始化，配置格式/级别/文件轮转/异步写入/彩色终端输出，替代 stdlib logging。
实现效果：日志统一可搜索，支持运行时动态调整日志级别，错误定位快。
技术栈：loguru (file rotation, async write, colorized output)

层&依赖：core 层，不依赖其他业务模块，仅被其他模块 import 使用
细节见文档：docs/docs_refactor/tech-stack.md → §日志系统、resilience.md → §日志系统
"""