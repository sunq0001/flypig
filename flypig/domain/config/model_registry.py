"""ModelRegistry dataclass

为什么做：可用模型的清单（provider/base_url/default_model/temperature）需要统一的结构化管理。
实现方法：@dataclass 定义 ModelRegistry（model_id/provider/url/temp 等字段），从 YAML 或 env 加载。
实现效果：加新模型只需在配置中添加一条记录，不需要改代码。
技术栈：@dataclass, 模型清单 + provider/temperature

层&依赖：domain.config 层，零依赖
细节见文档：docs/docs_refactor/backend-modules.md → §配置即代码
"""