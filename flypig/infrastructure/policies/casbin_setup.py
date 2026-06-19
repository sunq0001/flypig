"""Casbin 权限初始化

为什么做：文件/终端/git/test 等操作需要权限控制引擎，Casbin 提供声明式的策略管理。
实现方法：pycasbin Enforcer 初始化，加载 model.conf + policy.csv，注册到 DI 容器。
实现效果：权限策略集中管理，改策略只需改 CSV 文件。
技术栈：pycasbin Enforcer, model.conf + policy.csv 加载

层&依赖：infrastructure.policies 层，依赖 pycasbin
细节见文档：docs/docs_refactor/backend-modules.md → §PolicyService
"""
