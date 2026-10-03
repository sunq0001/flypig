"""Git Checkpoint 管理

为什么做：AI 修改了文件后，需要自动创建 git checkpoint 以便用户回滚到任意轮次的文件状态。
实现方法：GitCheckpointManager 封装 git init/commit/restore，turn_id → commit_hash 映射存于 conversation_store。~80 行。
实现效果：用户可以在历史回滚弹窗中"回到某轮修改前的状态"。
技术栈：git init/commit/restore, mapping→conversation_store 的 turn_id→commit_hash, ~80 行

层&依赖：orchestration 层，依赖 GitPython + IConversationStore（映射存储）
细节见文档：docs/docs_refactor/mem_convStore_checkpoints.md → §Git Checkpoint、backend-modules.md → §GitCheckpointManager
"""
