"""LSP 诊断接口

为什么做：AI 修改代码后需要检查语法错误，LSP 提供实时诊断。

实现方法：ILspDiagnostics ABC 定义 get_diagnostics(file_path) → [Diagnostic]。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod
from typing import Any


class ILspDiagnostics(ABC):
    """LSP 诊断接口 — 代码语法/类型错误检查"""

    @abstractmethod
    async def get_diagnostics(self, file_path: str) -> list[dict[str, Any]]: ...
