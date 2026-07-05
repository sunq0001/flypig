"""配置数据类包

为什么做：模型配置/项目配置需要类型安全的数据结构，不能裸用 dict。
实现方法：@dataclass 定义 Config 和 ModelRegistry 数据类，纯数据无 IO。
实现效果：配置读写类型安全，IDE 自动补全。
技术栈：@dataclass

层&依赖：domain.config 层，零依赖（纯 dataclass）
细节见文档：docs/docs_refactor/backend-modules.md → §配置即代码

使用方式：from domain.config import Config, REGISTRY, resolve, known_models
"""

from .config import Config
from .model_registry import REGISTRY, known_models, providers, resolve
