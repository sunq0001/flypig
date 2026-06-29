"""FlyPig 入口点

为什么做：用户需要通过一条命令启动整个 FlyPig 服务（Web / CLI 两种模式可选）。
实现方法：读取命令行参数 → 初始化 DI 容器 → 加载配置 → 启动 Quart（Hypercorn）或 CLI 接口。启动时检测崩溃恢复。
实现效果：`python -m flypig` 一条命令启动，无需复杂配置。
技术栈：argparse, DI 容器, Hypercorn

层&依赖：presentation 层（入口），依赖 core/container + core/app + resilience §崩溃恢复
细节见文档：docs/docs_refactor/resilience.md → §启动恢复流程
"""
