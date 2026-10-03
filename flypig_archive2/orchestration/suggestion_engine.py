"""评分→建议映射引擎

为什么做：AI 改完代码后需要根据 ChangeScore 生成对抗建议（哪些改得好、哪些有隐患、建议用户怎么操作）。
实现方法：generate_suggestion() 根据 ChangeScore + diff 生成建议文案和风险标记。~40 行自研。
实现效果：用户看到 AI 修改后的"第二意见"，帮助判断是否采纳 AI 的修改。
技术栈：generate_suggestion(), ~40 行自研

层&依赖：orchestration 层，依赖 domain/models/change_score.py
细节见文档：docs/docs_refactor/adversarial-system.md → §对抗建议、backend-modules.md → §SuggestionEngine
"""
