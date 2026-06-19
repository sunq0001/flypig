"""文件变更监控

为什么做：AI 修改文件后需要通知前端实时刷新文件树和编辑器，用户不需要手动刷新。
实现方法：watchdog 监控工作区文件变更，变更事件通过 SSE 推送到前端。
实现效果：AI 改文件，前端文件树和编辑器自动同步，用户无缝体验。
技术栈：watchdog, 文件修改→通知前端

层&依赖：backend 层，依赖 watchdog + SSE Queue
细节见文档：docs/docs_refactor/data-flow.md → §文件变更流
"""