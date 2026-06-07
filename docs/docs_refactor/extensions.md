# 扩展预留

> **来源**: `architecture-refactor.md` §3.7, §3.9
> **关联文档**: `backend-modules.md`（接口定义）、`subprocess-and-tools.md`（MCP 工具）
> 当前只定义接口 + 空实现，不实现具体逻辑。

## MCP 协议集成

通过 `mcp.json` 配置文件加载，`mcp_loader.py` 启动子进程连接 MCP 服务器，获取 tools 列表后注册到 LangGraph ToolNode。

**内置 MCP 注册表**：
```python
_MCP_REGISTRY = {
    "网页搜索": {"servers": ["@anthropic/mcp-server-web-search", "brave-search"],
                 "install": "npx @anthropic/mcp-server-web-search"},
    "网页抓取": {"servers": ["@anthropic/mcp-server-fetch"],
                 "install": "npx @anthropic/mcp-server-fetch"},
    "OCR文字识别": {"servers": ["mcp-server-ocr"],
                   "install": "uvx mcp-server-ocr"},
    "GitHub集成": {"servers": ["@anthropic/mcp-server-github"],
                   "install": "npx @anthropic/mcp-server-github"},
    "浏览器自动化": {"servers": ["@anthropic/mcp-server-playwright"],
                    "install": "npx @anthropic/mcp-server-playwright"},
    "数据库查询": {"servers": ["mcp-server-sqlite", "mcp-server-postgres"],
                  "install": "uvx mcp-server-sqlite"},
}
```

**v1**：AI 调用 `tool_mcp_install(server_name)` 仅返回安装命令字符串，由用户手动执行。
**v2（未来）**：在 Docker 沙箱内自动执行安装命令。

**mcp.json 配置文件**：
```json
{
  "mcpServers": {
    "web-search": {"command": "npx", "args": ["@anthropic/mcp-server-web-search"]},
    "fetch": {"command": "npx", "args": ["@anthropic/mcp-server-fetch"]}
  }
}
```

## 文件上传与压缩解压（§3.7.2）

文件上传前后端联动，用户在 Web Dashboard 拖拽/选择文件上传：

```
前端: Element Plus Upload 组件（支持拖拽、多文件、大文件分片）
后端: POST /api/upload → 保存到工作区临时目录
  → 检测到压缩包（.zip/.7z/.tar/.rar）→ 自动解压到同目录
  → 返回文件列表给前端

AI: 上传完成后自动感知新文件，可读取/分析
```

压缩解压工具（`tool_extract_archive` 供 AI 直接调用）：

```python
def _safe_extract_zip(archive: zipfile.ZipFile, target_dir: Path):
    """安全解压 zip，防止 zip slip 路径穿越"""
    for entry in archive.infolist():
        resolved = (target_dir / entry.filename).resolve()
        if not str(resolved).startswith(str(target_dir.resolve())):
            raise SecurityError(f"拒绝路径穿越: {entry.filename}")
        archive.extract(entry, target_dir)

def _safe_extract_tar(archive: tarfile.TarFile, target_dir: Path):
    for entry in archive.getmembers():
        resolved = (target_dir / entry.name).resolve()
        if not str(resolved).startswith(str(target_dir.resolve())):
            raise SecurityError(f"拒绝路径穿越: {entry.name}")
        archive.extract(entry, target_dir)

def tool_extract_archive(archive_path: str, target_dir: str = None) -> str:
    """自动识别格式并安全解压（防路径穿越攻击）"""
    target = Path(target_dir or Path(archive_path).parent).resolve()
    ext = Path(archive_path).suffix.lower()
    extractors = {
        ".zip": lambda: _safe_extract_zip(zipfile.ZipFile(archive_path), target),
        ".tar": lambda: _safe_extract_tar(tarfile.open(archive_path), target),
        ".7z": lambda: py7zr.SevenZipFile(archive_path).extractall(target),
        ".rar": lambda: rarfile.RarFile(archive_path).extractall(target),
    }
    if ext not in extractors:
        raise ValueError(f"不支持的压缩格式: {ext}")
    try:
        extractors[ext]()
        return f"解压完成: {archive_path} -> {target}"
    except SecurityError as e:
        return f"解压失败 - 安全限制: {e}"
```

**安全要点**：
- Zip Slip 防护：检查每个条目解析后的绝对路径是否以目标目录开头
- `.7z` 文件：py7zr >= 0.20 已有内置安全检查
- 依赖 `zipfile`/`tarfile`（标准库）+ `py7zr`/`rarfile`（可选）

## 存储抽象 + 代码知识图谱

### IRepository

```python
class IRepository(ABC):
    async def save_session(session) -> None: ...
    async def load_session(session_id) -> Optional[Session]: ...
    async def list_sessions(user, limit=20) -> List[Session]: ...
    async def delete_session(session_id) -> None: ...
```

## IHistoryStore

P0: IRepository（已有 SQLite）
P1: IHistoryStore 接口 + NoOp 空实现（当前）
P2: SQLite FTS5 全文搜索
P3: 成本监控 + 模式检测
P4: pgvector 向量搜索 + cross-encoder 重排
P5: Graphify 知识图谱实体查询

## IKnowledgeStore

```python
class IKnowledgeStore(ABC):
    async def index_project(project_root) -> None: ...
    async def search_entity(name, type) -> list[EntityLocation]: ...
    async def get_entity_relations(entity_name) -> list[Relation]: ...
    async def get_file_summary(file_path) -> FileSummary: ...
```
