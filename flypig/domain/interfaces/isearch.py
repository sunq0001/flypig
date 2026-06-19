"""搜索抽象接口

为什么做：代码搜索有多种方式（grep/AST/向量语义），需要统一接口便于切换和组合。
实现方法：ISearch ABC 定义 search(query) → results 核心方法，grep AST vector 各实现。
实现效果：上层代码不关心搜索怎么实现，换搜索方式不改调用代码。
技术栈：ISearch ABC, grep/AST/vector 多实现

层&依赖：domain.interfaces 层，零依赖
细节见文档：docs/docs_refactor/tech-stack.md → §代码检索
"""