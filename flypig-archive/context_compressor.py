"""Tree-sitter 上下文压缩模块

通过 AST 解析，将大文件的函数/方法/类体替换为占位符，
保留签名、导入、常量等关键结构信息，减少 Token 消耗。
"""

from pathlib import Path
from typing import Dict, List, Set

import tree_sitter as ts


# 文件扩展名 -> tree-sitter 语言名
EXTENSION_MAP: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".rb": "ruby",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".mdx": "markdown",
}

# 各语言中"函数/方法定义"节点的类型 — 只有这类节点的 body 才被压缩
FUNCTION_DEF_TYPES: Dict[str, Set[str]] = {
    "python": {"function_definition", "lambda"},
    "javascript": {
        "function_declaration",
        "method_definition",
        "arrow_function",
        "generator_function_declaration",
    },
    "typescript": {
        "function_declaration",
        "method_definition",
        "arrow_function",
        "generator_function_declaration",
    },
    "go": {"function_declaration", "method_declaration", "func_literal"},
    "rust": {"function_item", "closure_expression"},
    "java": {"method_declaration", "lambda_expression"},
    "cpp": {"function_definition", "lambda_expression"},
    "c": {"function_definition"},
    "ruby": {"method"},
}

# 各语言中表示"代码体"的 AST 节点类型
BODY_NODE_TYPES: Set[str] = {
    "block",  # Python, Go, Ruby, C, C++
    "statement_block",  # JavaScript, TypeScript
    "class_body",  # JavaScript, TypeScript, Java
    "body",  # some grammars
    "declaration_list",  # Rust (impl/trait items), Go
    "module_body",  # some grammars
    "object",  # Go type struct body
}

# 触发压缩的阈值（函数/类体超过多少行则压缩）
BODY_LINE_THRESHOLD: int = 15

# 最少压缩比例（压缩后需比原内容小多少比例才使用）
MIN_COMPRESSION_RATIO: float = 0.7


class TreeSitterCompressor:
    """使用 Tree-sitter 对代码进行上下文压缩"""

    def __init__(self):
        self._languages: Dict[str, object] = {}
        self._parsers: Dict[str, object] = {}

    def _get_parser(self, lang_name: str):
        """按需加载语言包并创建 parser"""
        if lang_name in self._parsers:
            return self._parsers[lang_name]

        try:
            import importlib

            module = importlib.import_module(f"tree_sitter_{lang_name}")
            capsule = module.language()
            language = ts.Language(capsule)
            parser = ts.Parser(language)
            self._parsers[lang_name] = parser
            return parser
        except ImportError:
            return None
        except Exception:
            return None

    def compress(
        self, content: str, file_path: str = "", max_chars: int = 50000
    ) -> str:
        """压缩代码内容

        Args:
            content: 原始代码
            file_path: 文件路径（用于推断语言）
            max_chars: 最大字符数

        Returns:
            压缩后的代码，或压缩收益不足时返回原始代码
        """
        # 小文件不压缩
        if len(content) <= max_chars * 0.3:
            return content

        lang_name = EXTENSION_MAP.get(Path(file_path).suffix.lower())
        if not lang_name:
            return content

        parser = self._get_parser(lang_name)
        if not parser:
            return content

        try:
            tree = parser.parse(bytes(content, "utf-8"))
            body_lines = self._find_large_bodies(
                tree.root_node, lang_name, BODY_LINE_THRESHOLD
            )

            if not body_lines:
                return content

            compressed = self._collapse_lines(content, body_lines)

            # 只有压缩收益足够才使用压缩版本
            if len(compressed) < len(content) * MIN_COMPRESSION_RATIO:
                return compressed

            return content
        except Exception:
            return content

    def _find_large_bodies(
        self, node, lang_name: str, threshold: int, parent_is_func: bool = False
    ) -> Set[int]:
        """递归查找大函数/方法体内的大段代码，返回需要移除的行号集合

        Args:
            node: 当前 AST 节点
            lang_name: 语言名称
            threshold: 触发压缩的最小行数
            parent_is_func: 当前节点的父节点是否为函数/方法定义

        策略：
        - 仅在 函数/方法定义 的直接子节点中才折叠 body（保留签名）
        - 类定义和容器节点的 body 不折叠（保留类内方法签名）
        """
        lines: Set[int] = set()
        func_def_types = FUNCTION_DEF_TYPES.get(lang_name, set())

        for child in node.named_children:
            child_is_func = child.type in func_def_types

            # 仅当父节点是函数定义时，折叠大 body
            if child.type in BODY_NODE_TYPES and parent_is_func:
                line_count = child.end_point[0] - child.start_point[0]
                if line_count > threshold:
                    lines.update(range(child.start_point[0], child.end_point[0] + 1))

            # 递归：如果当前 child 是函数定义，向下传递 parent_is_func=True
            lines.update(
                self._find_large_bodies(child, lang_name, threshold, child_is_func)
            )

        return lines

    def _collapse_lines(self, content: str, body_lines: Set[int]) -> str:
        """根据要移除的行号构建压缩后的内容"""
        lines = content.split("\n")
        result: List[str] = []
        i = 0

        while i < len(lines):
            if i in body_lines:
                # 获取缩进
                indent = len(lines[i]) - len(lines[i].lstrip())
                count = 0
                while i < len(lines) and i in body_lines:
                    count += 1
                    i += 1
                placeholder = f"{' ' * indent}... ({count} lines)"
                result.append(placeholder)
            else:
                result.append(lines[i])
                i += 1

        return "\n".join(result)
