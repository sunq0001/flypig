"""权限检查单元测试

为什么做：Casbin 权限策略需要测试，确保 allow/ask/deny 三种结果正确返回。
实现方法：pytest 参数化，测试不同 sub/obj/act 组合的 check_permission 结果。
实现效果：权限策略变更后测试可验证策略是否按预期生效。
技术栈：pytest, Casbin mock

层&依赖：tests.unit 层，依赖 infrastructure/policies/permission_checker.py
细节见文档：docs/docs_refactor/mode-matrix.md → §工具可用性
"""