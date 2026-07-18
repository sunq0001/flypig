"""MCP 统一网关 — 加载 MCP 服务器，代理工具到 @tool 注册表

为什么做：FlyPig 的 LLM 需要通过 `@tool` 注册表统一调用所有工具。
         外部 MCP 服务器（Chrome DevTools、Playwright 等）需要桥接
         到这个注册表，走同一个 ReAct 循环（execute → chat）。

实现方法：
  1. MCPGateway 读取 mcp.json 配置
  2. 为每个 MCP 服务器启动子进程（stdio JSON-RPC）
  3. 调用 tools/list 发现所有可用工具
  4. 自动生成 @tool 装饰器包装类，注册到 _TOOL_REGISTRY
  5. LLM 调工具 → ToolExecutor → MCPGateway → tools/call → 返回结果

工作方式：
  - 启动时自动连接已配置的 MCP 服务器
  - 支持动态启用/禁用（tool_mcp_lifecycle）
  - 超时 + 断线重连

层&依赖：infrastructure.tools.mcp 层，依赖 subprocess + json + registry
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from flypig.data import get_registry_path
from flypig.infrastructure.tools.registry import tool

# ── MCP 配置（数据来源：model_registry.json → mcp 段）──


def _load_mcp_cfg() -> dict:
    """读取 model_registry.json 的 mcp 配置段"""
    try:
        with open(get_registry_path(), encoding="utf-8") as f:
            return json.load(f).get("mcp", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# 模块加载时一次读取，运行期不变（热加载重启进程时会重新 import）
# 全部用 .get() + 默认值，避免 model_registry.json mcp 段缺键导致 KeyError
_MCP_CFG = _load_mcp_cfg()
_MCP_PROTOCOL: str = _MCP_CFG.get("protocol_version", "0.1.0")
_MCP_CLIENT_INFO: dict = _MCP_CFG.get("client_info", {"name": "flypig", "version": "0.1.0"})
_MCP_HANDSHAKE_TIMEOUT: int = _MCP_CFG.get("handshake_timeout", 10)
_MCP_TOOL_CALL_TIMEOUT: int = _MCP_CFG.get("tool_call_timeout", 60)
_MCP_TOOL_PREFIX: str = _MCP_CFG.get("tool_name_prefix", "mcp")
_MCP_SERVERS: dict = _MCP_CFG.get("servers", {})


class MCPServerProcess:
    """管理单个 MCP 服务器的子进程 + JSON-RPC 通信"""

    def __init__(self, name: str, command: str, args: list[str], cwd: str | None = None) -> None:
        self.name = name
        self._command = command
        self._args = args
        self._cwd = cwd
        self._process: asyncio.subprocess.Process | None = None
        self._tools: list[dict] = []
        self._req_id = 0

    async def start(self) -> None:
        """启动 MCP 服务器子进程"""
        if self._process and self._process.returncode is None:
            return  # 已在运行

        self._process = await asyncio.create_subprocess_exec(
            self._command,
            *self._args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._cwd,
        )

        # 等待就绪：先发 tools/list 确认
        try:
            await asyncio.wait_for(self._handshake(), timeout=_MCP_HANDSHAKE_TIMEOUT)
        except (TimeoutError, Exception) as e:
            await self.stop()
            raise RuntimeError(f"MCP [{self.name}] 启动失败: {e}") from e

    async def _handshake(self) -> None:
        """发送 initialize + tools/list 握手"""
        # 初始化（协议版本/客户端信息从 model_registry.json 读取）
        await self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": _MCP_PROTOCOL,
                    "capabilities": {},
                    "clientInfo": _MCP_CLIENT_INFO,
                },
            }
        )
        init_resp = await self._recv()
        if not init_resp or "result" not in init_resp:
            raise RuntimeError(f"初始化失败: {init_resp}")

        # 发送 initialized 通知
        await self._send(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
        )

        # 发现工具
        await self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list",
            }
        )
        list_resp = await self._recv()
        if list_resp and "result" in list_resp:
            self._tools = list_resp["result"].get("tools", [])

    async def discover_tools(self) -> list[dict]:
        """获取此服务器提供的工具列表（OpenAI format）"""
        return list(self._tools)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """调用 MCP 工具并返回结果"""
        await self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        resp = await asyncio.wait_for(self._recv(), timeout=_MCP_TOOL_CALL_TIMEOUT)
        if not resp:
            return f"[Error] MCP [{self.name}] 无响应"

        if "error" in resp:
            return f"[Error] MCP [{self.name}] {resp['error'].get('message', str(resp['error']))}"

        content = resp.get("result", {}).get("content", [])
        texts = [
            item.get("text", json.dumps(item, ensure_ascii=False))
            for item in content
            if isinstance(item, dict)
        ]
        return "\n".join(texts) if texts else json.dumps(resp.get("result", {}), ensure_ascii=False)

    async def stop(self) -> None:
        """停止 MCP 服务器子进程"""
        if self._process and self._process.returncode is None:
            try:
                self._process.kill()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except Exception:
                pass
        self._process = None

    async def health(self) -> bool:
        """检查进程是否存活"""
        return self._process is not None and self._process.returncode is None

    # ── JSON-RPC 通信 ──

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def _send(self, msg: dict) -> None:
        if not self._process or not self._process.stdin:
            raise RuntimeError("MCP 进程未启动")
        line = json.dumps(msg, ensure_ascii=False) + "\n"
        self._process.stdin.write(line.encode("utf-8"))
        await self._process.stdin.drain()

    async def _recv(self) -> dict | None:
        if not self._process or not self._process.stdout:
            return None
        line = await self._process.stdout.readline()
        if not line:
            return None
        return json.loads(line.decode("utf-8").strip())


class MCPGateway:
    """MCP 统一网关 — 管理多个 MCP 服务器，注册工具到 @tool 注册表"""

    def __init__(self, servers: dict | None = None) -> None:
        self._servers: dict[str, MCPServerProcess] = {}
        self._loaded = False
        self._servers_config = servers if servers is not None else _MCP_SERVERS
        self._stderr_tasks: list[asyncio.Task] = []

    async def load_all(self) -> list[dict]:
        """加载所有 MCP 服务器，发现工具，注册到 @tool 注册表

        服务器列表来自 model_registry.json → mcp.servers
        不读任何 IDE 配置文件（.codebuddy/ 等）

        Returns:
            所有发现的工具 schema 列表
        """
        if self._loaded:
            return self._get_all_tool_schemas()

        if not self._servers_config:
            return []

        for name, cfg in self._servers_config.items():
            try:
                await self._load_server(name, cfg)
            except Exception as e:
                print(f"  [mcp] {name}: 加载失败 - {e}")

        self._loaded = True
        return self._get_all_tool_schemas()

    async def _load_server(self, name: str, cfg: dict) -> None:
        """加载单个 MCP 服务器"""
        command = cfg.get("command", "")
        args = cfg.get("args", [])
        cwd = cfg.get("cwd")

        server = MCPServerProcess(name, command, args, cwd)
        await server.start()
        self._servers[name] = server

        # 读取 stderr（MCP 服务器可能在这输出日志）
        if server._process and server._process.stderr:
            task = asyncio.create_task(self._pipe_stderr(name, server))
            self._stderr_tasks.append(task)

        # 发现工具 → 注册到 @tool 注册表
        tools = await server.discover_tools()
        for tool_def in tools:
            self._register_mcp_tool(name, tool_def, server)

        print(f"  [mcp] {name}: {len(tools)} 个工具已注册")

    def _register_mcp_tool(
        self, server_name: str, tool_def: dict, server: MCPServerProcess
    ) -> None:
        """将 MCP 工具动态注册到 @tool 注册表"""
        tool_name = tool_def.get("name", "")
        description = tool_def.get("description", "")

        # 防止名字冲突：加前缀 {prefix}_{server_name}_
        prefixed_name = f"{_MCP_TOOL_PREFIX}_{server_name}_{tool_name}"

        # 构建参数 schema
        input_schema = tool_def.get("inputSchema", {})
        properties = input_schema.get("properties", {})

        # 使用 @tool 装饰器动态注册
        @tool(
            name=prefixed_name,
            category=f"mcp/{server_name}",
            timeout=120,
            description=f"[MCP {server_name}] {description}",
        )
        class _DynamicMCPTool:
            """动态生成的 MCP 工具包装类"""

            async def __call__(self, **kwargs: Any) -> str:
                """转发到 MCP 服务器"""
                # 只传 inputSchema 里定义的参数
                filtered = {k: v for k, v in kwargs.items() if k in properties}
                return await server.call_tool(tool_name, filtered)

        # schema 由 @tool 装饰器 + executor 自动处理

    async def _pipe_stderr(self, name: str, server: MCPServerProcess) -> None:
        """管道读取 MCP 服务器的 stderr（调试用）"""
        if not server._process or not server._process.stderr:
            return
        try:
            async for line in server._process.stderr:
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    pass  # print(f"  [mcp:{name}] {text}")
        except Exception:
            pass

    def _get_all_tool_schemas(self) -> list[dict]:
        """获取所有已发现工具的 schema"""
        schemas = []
        for server in self._servers.values():
            schemas.extend(server._tools)
        return schemas

    async def shutdown_all(self) -> None:
        """停止所有 MCP 服务器"""
        for name, server in self._servers.items():
            try:
                await server.stop()
            except Exception as e:
                print(f"  [mcp] {name}: 停止失败 - {e}")
        self._servers.clear()

    def get_servers(self) -> dict[str, MCPServerProcess]:
        """获取所有已加载的 MCP 服务器"""
        return dict(self._servers)


# ── 全局单例 — 供 ToolExecutor 调用 ──
_gateway: MCPGateway | None = None


async def init_mcp_gateway() -> MCPGateway:
    """初始化全局 MCP 网关（服务器列表来自 model_registry.json → mcp.servers）"""
    global _gateway
    if _gateway is None:
        _gateway = MCPGateway()
        await _gateway.load_all()
    return _gateway


def get_mcp_gateway() -> MCPGateway | None:
    """获取全局 MCP 网关实例"""
    return _gateway


__all__ = [
    "MCPGateway",
    "MCPServerProcess",
    "get_mcp_gateway",
    "init_mcp_gateway",
]
