"""Casbin 权限封装

为什么做：文件/终端/git/test 等操作需要权限控制（allow/ask/deny），不能所有操作都直接放行。
实现方法：PolicyService 封装 pycasbin Enforcer，基于 model.conf + policy.csv 判断权限。~80 行。
实现效果：修改权限策略只需改 policy.csv，不需要改业务代码。
技术栈：pycasbin, allow/ask/deny, ~80 行

层&依赖：orchestration 层，依赖 infrastructure/policies（Casbin 配置）
细节见文档：docs/docs_refactor/backend-modules.md → §PolicyService、mode-matrix.md → §权限矩阵
"""
