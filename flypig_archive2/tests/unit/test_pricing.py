"""价格计算单元测试

为什么做：模型价格的获取和缓存逻辑需要测试，确保费用计算准确。
实现方法：mock 外部 API，测试价格获取/缓存命中/费用计算。
实现效果：价格更新后费用计算仍准确。
技术栈：pytest, mock API

层&依赖：tests.unit 层，依赖 infrastructure/usage/pricing.py
细节见文档：docs/docs_refactor/mem_convStore_usage.md → §模型定价
"""
