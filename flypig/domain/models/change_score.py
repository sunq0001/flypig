"""变更评分数据类

为什么做：AI 修改代码前需要评估影响范围，按风险等级决定审批方式（自动/通知/阻塞）。
实现方法：@dataclass 定义 ChangeScore (level: TRIVIAL/LOW/MEDIUM/HIGH/CRITICAL, risk_reason, affected_files)。
实现效果：根据 ChangeScore 等级自动选择审批策略，用户不用手工审核 trivial 变更。
技术栈：@dataclass, ChangeScore: TRIVIAL/LOW/MEDIUM/HIGH/CRITICAL

层&依赖：domain.models 层，零依赖
细节见文档：docs/docs_refactor/adversarial-system.md → §ChangeScore
"""