"""AST 解析接口

为什么做：定位代码中的符号（函数/类/变量）需要 AST 解析，而不是靠正则硬搜。
实现方法：IASTParser ABC 定义 parse_symbol(symbol) → (file, line) 方法，tree-sitter 实现。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod


class IASTParser(ABC):
    """AST 解析接口 — 根据符号名定位文件和行号"""

    @abstractmethod
    async def parse_symbol(self, symbol: str) -> tuple[str, int] | None: ...
