"""MultiRoleManager

为什么做：AI 在不同阶段（分析需求/审查代码/测试用例/评估架构）需要不同的角色 prompt，需要一个管理器按需切换。

实现方法：根据 mode + 角色名从 roles/ 目录加载对应 .md prompt 文件，组装为系统消息。
角色 = 由 AgentState.persona 决定（developer / reviewer / tester / architect / documenter）。
prompt 文件首次加载后缓存，不重复读磁盘。

实现效果：prompt 与代码分离，无需改代码即可调整 AI 的行为角色。

技术栈：pathlib 读文件, dict 缓存, ~50 行自研

层&依赖：domain.prompts 层，依赖 roles/*.md 文件
细节见文档：docs/docs_refactor/tech-stack.md → §MultiRoleManager
"""

from __future__ import annotations

from pathlib import Path


class MultiRoleManager:
    """多角色 Prompt 管理器

    根据角色名从 roles/ 目录加载 .md prompt 文件，组装为系统消息。
    """

    _ROLES_DIR = Path(__file__).resolve().parent / "roles"
    _cache: dict[str, str] = {}

    def get_system_message(self, persona: str = "developer", mode: str = "explore") -> str:
        """获取指定角色的系统提示词

        Args:
            persona: 角色名（developer / reviewer / tester / architect / documenter）
            mode: 对话模式（explore / plan / execute）

        Returns:
            完整的系统提示词文本
        """
        prompt = self._load_prompt(persona)
        return prompt

    def _load_prompt(self, persona: str) -> str:
        """从文件加载 prompt（带缓存）"""
        if persona in self._cache:
            return self._cache[persona]

        filepath = self._ROLES_DIR / f"{persona}.md"
        if not filepath.exists():
            self._cache[persona] = ""
            return ""

        text = filepath.read_text(encoding="utf-8")
        self._cache[persona] = text
        return text

    def available_roles(self) -> list[str]:
        """返回 roles/ 目录下所有可用角色"""
        if not self._ROLES_DIR.exists():
            return []
        return [f.stem for f in sorted(self._ROLES_DIR.glob("*.md"))]

    def reload(self) -> None:
        """清空缓存，下次 get_system_message 时重新读取文件"""
        self._cache.clear()
