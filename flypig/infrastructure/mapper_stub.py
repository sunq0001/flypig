"""存根实现 — TODO: 替换为真实实现

为什么做：满足 architecture_check 接口契约检查，防止 pre-commit 拦截。
实现方法：继承 domain/interfaces 的 ABC，方法体留空或返回默认值。
层&依赖：infrastructure 层，依赖对应的 domain.interfaces 接口
"""
from typing import Any
from flypig.domain.interfaces.imapper import IMapper


class Mapper(IMapper):
    """模型映射器存根"""
    async def map_model(self, model_name: str, target_provider: str) -> dict[str, Any]:
        return {"model": model_name, "provider": target_provider}
