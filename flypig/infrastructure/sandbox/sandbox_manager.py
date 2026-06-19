"""Docker 沙箱生命周期管理器

为什么做：AI 的命令执行优先在 Docker 沙箱内运行（安全隔离），沙箱不可用时降级本地。
实现方法：SandboxManager 管理 Docker 容器生命周期（create/exec/stop/remove）+ 状态检测，失败降级时通知前端。
实现效果：AI 命令在隔离环境执行，不污染宿主机。Docker 不可用时自动降级本地，不中断服务。
技术栈：Docker SDK, check/down 降级通知

层&依赖：infrastructure.sandbox 层，依赖 Docker SDK + subprocess
细节见文档：docs/docs_refactor/subprocess.md → §执行策略
"""