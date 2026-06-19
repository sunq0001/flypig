"""变更审查数据生成工具

为什么做：AI 改代码前需要生成结构化的变更计划（改了哪些文件/函数/行/风险等级），用户改前就能知道影响范围。
实现方法：解析 AI 生成的 diff，提取变更类型（add/modify/delete_function/line）、符号名、diff 摘要、风险自评。
实现效果：用户审批前看到"AI 打算改什么、影响范围、风险等级"，而不是改完再发现不对。
技术栈：diff_excerpt, risk 自评, 结构化成 plan

层&依赖：infrastructure.tools.review 层，依赖 tools/file（读文件比较）
细节见文档：docs/docs_refactor/adversarial-system.md → §ChangePlan
"""