"""Git 回滚路由 (/api/rollback)

为什么做：用户需要将工作区文件回滚到某轮 AI 修改前的状态，通过 turn_id 找到对应的 git commit。
实现方法：POST /api/rollback/<turn_id> → 查 checkpoint_mappings 表 → commit_hash → git checkout。POST /api/rollback/search 自然语言搜索。
实现效果：用户选中某轮历史后一键回滚文件状态。
技术栈：GitPython, turn_id → commit_hash, POST

层&依赖：backend.routes 层，依赖 orchestration/git_checkpoint_manager.py
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点
"""