# 扩展预留

> **来源**: `architecture-refactor.md` §3.7, §3.9
> **关联文档**: `backend-modules.md`（接口定义）、`subprocess-and-tools.md`（MCP 工具）
> 当前只定义接口 + 空实现，不实现具体逻辑。

## MCP 协议集成

### 三层策略：基础配置 → AI 按需发现 → 安装

**第一层：基础配置（项目自带，开箱即用）**

项目默认附带 `mcp.json`，预装最常用的 MCP 服务器，用户零操作即可使用：

```json
{
  "mcpServers": {
    "web-search": {"command": "npx", "args": ["@anthropic/mcp-server-web-search"]},
    "fetch": {"command": "npx", "args": ["@anthropic/mcp-server-fetch"]}
  }
}
```

`mcp_loader.py` 启动时自动加载此文件，连接 MCP 服务器，将 tools 注册到 LangGraph ToolNode。

**第二层：AI 按需发现（AI 主动询问用户）**

当 AI 发现当前任务需要基础配置中没有的能力时，主动搜索内置注册表并询问用户：

```
AI: "我需要进行网页搜索来查这个 API 文档，但当前没有搜索能力。
     找到可装的 MCP 服务器：网页搜索 (npx @anthropic/mcp-server-web-search)
     要装吗？"
    → 用户[批准] → 执行安装 → 写入 mcp.json → mcp_loader 热加载
    → 用户[拒绝] → AI 换方案
```

内置注册表（预置已知的 MCP 服务器信息）：

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

以 `tool_mcp_search(requirement)` 供 AI 调用，搜索注册表找到匹配的服务器。

**第三层：安装执行**

| 版本 | 方式 | 说明 |
|------|------|------|
| **v1** | 提示用户手动 | `tool_mcp_install` 仅返回安装命令字符串，用户复制到终端执行 |
| **v2（未来）** | Docker 沙箱自动 | `tool_mcp_install` 在 Docker 沙箱内自动执行，自动写入 mcp.json，mcp_loader 动态加载 |

用户也可以自行编辑 `mcp.json` 添加自定义 MCP 服务器（如企业内部 API），无需通过 AI。

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
