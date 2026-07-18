"""工作区聚合根

为什么做：每个项目目录作为一个工作区，管理路径和相关配置。
实现方法：Workspace(AggregateRoot) 封装路径验证和上下文管理。

层&依赖：domain 层，依赖 shared
"""

from pathlib import Path
from flypig.shared.base import AggregateRoot


class Workspace(AggregateRoot):
    """工作区聚合根 — 管理项目目录"""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path).resolve()
        self._name = self._path.name

    @property
    def path(self) -> Path:
        return self._path

    @property
    def name(self) -> str:
        return self._name

    def is_valid(self) -> bool:
        """TODO: 验证工作区目录是否存在"""
        return self._path.exists()

    def list_files(self) -> list[Path]:
        """TODO: 获取工作区下的文件列表"""
        ...

    def contains(self, file_path: Path) -> bool:
        """TODO: 判断文件是否属于此工作区"""
        return str(file_path).startswith(str(self._path))
