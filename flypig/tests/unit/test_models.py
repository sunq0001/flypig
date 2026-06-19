"""数据类单元测试

为什么做：Message/Session/Task 等 dataclass 需要测试构造/验证/序列化。
实现方法：pytest 测试每个数据类的构造、字段验证、to_dict/from_dict 序列化。
实现效果：数据类变更后有测试覆盖，不会因改字段名导致运行时错误。
技术栈：pytest, dataclass 构造/验证

层&依赖：tests.unit 层，依赖 domain/models/*.py
细节见文档：docs/docs_refactor/backend-modules.md → §数据类型规范
"""
