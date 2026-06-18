# MCP 协议集成

> **来源**: `architecture-refactor.md` §3.7.1
> **关联文档**: `tools.md`（工具列表）、`backend-modules.md`（ToolExecutor 注册）
> 涉及 MCP 服务器的配置、发现、安装流程。

## 三层策略

### 第一层：基础配置（项目自带，开箱即用）

项目默认附带 `mcp.json`，预装最常用的 MCP 服务器，用户零操作即可使用：

```json
{
  "mcpServers": {
    "web-search": {"command": "npx", "args": ["@anthropic/mcp-server-web-search"]},
    "fetch": {"command": "npx", "args": ["@anthropic/mcp-server-fetch"]}
  }
}
```

`tool_mcp_loader.py` 启动时自动加载此文件，连接 MCP 服务器，将 tools 注册到 LangGraph ToolNode。

### 第二层 + 第三层：AI 按需发现 + 自动安装

不自研注册表和安装逻辑——直接使用 `mcp-auto-install`（`pip install mcp-auto-install`）。

`mcp-auto-install` 是一个 MCP 服务器，让 AI 通过自然语言发现、安装和管理其他 MCP 服务器：

```
AI 遇到需要搜索网页但没装搜索能力：
  → 调用 mcp-auto-install 提供的 install_mcp_server 工具
  → mcp-auto-install 自动搜索官方 MCP Registry
  → 找到 @anthropic/mcp-server-web-search
  → 用户[批准] → 自动下载安装 + 写入 mcp.json
  → tool_mcp_loader 热加载 → 注册到 ToolNode
  → AI 立即可用
```

| 能力 | 手写方案 | mcp-auto-install |
|------|---------|----------------|
| 搜索注册表 | 手写 `_MCP_REGISTRY` 字典 | 搜索**官方 MCP Registry** |
| 安装执行 | 仅提示命令字符串 | 自动 npm/pip 安装 + 写 mcp.json |
| 服务器范围 | 限于内置 6 个 | 官方 Registry 全部服务器 |
| 维护成本 | 需手动更新注册表 | 社区维护，自动更新 |

配置方式：在 `mcp.json` 中添加 `mcp-auto-install` 作为标准 MCP 服务器：

```json
{
  "mcpServers": {
    "web-search": {"command": "npx", "args": ["@anthropic/mcp-server-web-search"]},
    "fetch": {"command": "npx", "args": ["@anthropic/mcp-server-fetch"]},
    "auto-install": {"command": "npx", "args": ["@anthropic/mcp-auto-install"]}
  }
}
```

> **安全**：mcp-auto-install 安装时弹审批卡片，显示服务器信息，用户批准后才执行安装。

## 文件列表

| 文件 | 职责 |
|------|------|
| `infrastructure/tools/mcp/tool_mcp_loader.py` | 启动时加载 mcp.json，连接服务器，注册到 ToolNode |
| `infrastructure/tools/mcp/tool_mcp_manager.py` | MCP 自助安装（调用 mcp-auto-install） |
| `mcp.json` | MCP 服务器配置文件（项目根目录） |
