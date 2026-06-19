"""许可激活接口 (P2 预留)

为什么做：SaaS 版本需要验证用户许可证，开源版 NoOp 不执行任何操作。
实现方法：ILicenseService ABC 定义 check/activate/deactivate 方法，默认 NoOpLicenseService 实现。
实现效果：预留接口不影响现有代码，后续加 SaaS 许可证只需换实现。
技术栈：ILicenseService ABC, NoOp 默认实现

层&依赖：domain.interfaces 层，零依赖
细节见文档：—
"""