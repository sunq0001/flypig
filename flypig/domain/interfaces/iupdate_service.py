"""自动更新接口 (P2 预留)

为什么做：需要让用户感知到有新版可用，并提供一键更新能力。开源版 NoOp。
实现方法：IUpdateService ABC 定义 check/install 方法，NoOp 实现默认返回"无更新"。
实现效果：预留接口不影响现有代码，后续加更新机制只需换实现。
技术栈：IUpdateService ABC, NoOp 默认实现

层&依赖：domain.interfaces 层，零依赖
细节见文档：—
"""