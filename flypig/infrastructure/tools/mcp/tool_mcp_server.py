"""MCPServerProcess — 单个 MCP 服务器的子进程与 JSON-RPC 通信

为什么做：外部 MCP 服务器通过 stdio JSON-RPC 通信，需要独立管理子进程生命周期、
         握手、工具发现与调用；把「传输层」与网关的「注册/分发」职责分开，
         两边都保持单一职责与可测性。
实现方法：asyncio.create_subprocess_exec 启动子进程，按 MCP 协议依次发送
         initialize → notifications/initialized → tools/list，并封装 tools/call。
层&依赖：infrastructure.tools.mcp 层，依赖 asyncio + json + domain.exceptions
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from loguru import logger as _log

from flypig.data import get_registry_path
from flypig.domain.exceptions import MCPError

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
MCP_CFG: dict = _load_mcp_cfg()
MCP_PROTOCOL: str = MCP_CFG.get("protocol_version", "0.1.0")
MCP_CLIENT_INFO: dict = MCP_CFG.get("client_info", {"name": "flypig", "version": "0.1.0"})
MCP_TOOL_PREFIX: str = MCP_CFG.get("tool_name_prefix", "mcp")
MCP_SERVERS: dict = MCP_CFG.get("servers", {})

# ── 默认超时（秒）──
_DEFAULT_HANDSHAKE_TIMEOUT = 10
_DEFAULT_TOOL_CALL_TIMEOUT = 60
_STOP_TIMEOUT = 5

MCP_HANDSHAKE_TIMEOUT: int = MCP_CFG.get("handshake_timeout", _DEFAULT_HANDSHAKE_TIMEOUT)
MCP_TOOL_CALL_TIMEOUT: int = MCP_CFG.get("tool_call_timeout", _DEFAULT_TOOL_CALL_TIMEOUT)

# ── JSON-RPC 字段名 ──
_KEY_RESULT = "result"
_KEY_ERROR = "error"
_KEY_METHOD = "method"
_KEY_ID = "id"

# ── JSON-RPC 方法名 ──
_METHOD_INITIALIZE = "initialize"
_METHOD_INITIALIZED = "notifications/initialized"
_METHOD_LIST_TOOLS = "tools/list"
_METHOD_CALL_TOOL = "tools/call"
_JSONRPC_KEY = "jsonrpc"
_JSONRPC_VERSION = "2.0"


def _tag(server_name: str) -> str:
    """错误/日志前缀：MCP [服务器名]"""
    return f"MCP [{server_name}]"


def _require_init_response(server_name: str, resp: dict | None) -> None:
    """校验 initialize 响应，失败即抛 MCPError"""
    if not resp or _KEY_RESULT not in resp:
        raise MCPError(f"{_tag(server_name)} 初始化失败: {resp}")


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

        # 等待就绪：先发 initialize + tools/list 确认
        try:
            await asyncio.wait_for(self._handshake(), timeout=MCP_HANDSHAKE_TIMEOUT)
        except Exception as e:
            await self.stop()
            raise MCPError(f"{_tag(self.name)} 启动失败: {e}") from e

    async def _handshake(self) -> None:
        """发送 initialize + tools/list 握手"""
        try:
            await self._send(
                {
                    _JSONRPC_KEY: _JSONRPC_VERSION,
                    _KEY_ID: self._next_id(),
                    _KEY_METHOD: _METHOD_INITIALIZE,
                    "params": {
                        "protocolVersion": MCP_PROTOCOL,
                        "capabilities": {},
                        "clientInfo": MCP_CLIENT_INFO,
                    },
                }
            )
            init_resp = await self._recv()
            _require_init_response(self.name, init_resp)

            # 发送 initialized 通知
            await self._send({_JSONRPC_KEY: _JSONRPC_VERSION, _KEY_METHOD: _METHOD_INITIALIZED})

            # 发现工具
            await self._send(
                {
                    _JSONRPC_KEY: _JSONRPC_VERSION,
                    _KEY_ID: self._next_id(),
                    _KEY_METHOD: _METHOD_LIST_TOOLS,
                }
            )
            list_resp = await self._recv()
        except MCPError as e:
            _log.warning("[mcp:{}] 握手失败: {}", self.name, e)
            raise
        except Exception as e:
            raise MCPError(f"{_tag(self.name)} 握手失败: {e}") from e

        if list_resp and _KEY_RESULT in list_resp:
            self._tools = list_resp[_KEY_RESULT].get("tools", [])

    async def discover_tools(self) -> list[dict]:
        """获取此服务器提供的工具列表（OpenAI format）"""
        return list(self._tools)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """调用 MCP 工具并返回结果"""
        await self._send(
            {
                _JSONRPC_KEY: _JSONRPC_VERSION,
                _KEY_ID: self._next_id(),
                _KEY_METHOD: _METHOD_CALL_TOOL,
                "params": {"name": name, "arguments": arguments},
            }
        )
        resp = await asyncio.wait_for(self._recv(), timeout=MCP_TOOL_CALL_TIMEOUT)
        if not resp:
            return f"[Error] MCP [{self.name}] 无响应"

        if _KEY_ERROR in resp:
            err = resp[_KEY_ERROR]
            return f"[Error] MCP [{self.name}] {err.get('message', str(err))}"

        content = resp.get(_KEY_RESULT, {}).get("content", [])
        texts = [
            item.get("text", json.dumps(item, ensure_ascii=False))
            for item in content
            if isinstance(item, dict)
        ]
        result_data = resp.get(_KEY_RESULT, {})
        return "\n".join(texts) if texts else json.dumps(result_data, ensure_ascii=False)

    async def stop(self) -> None:
        """停止 MCP 服务器子进程"""
        if self._process and self._process.returncode is None:
            try:
                self._process.kill()
                await asyncio.wait_for(self._process.wait(), timeout=_STOP_TIMEOUT)
            except Exception as e:
                # 进程可能已自行退出，记录后继续清理引用
                _log.debug("[mcp:{}] 停止进程时异常: {}", self.name, e)
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
            raise MCPError("MCP 进程未启动")
        line = json.dumps(msg, ensure_ascii=False) + "\n"
        try:
            self._process.stdin.write(line.encode("utf-8"))
            await self._process.stdin.drain()
        except Exception as e:
            raise MCPError(f"{_tag(self.name)} 发送消息失败: {e}") from e

    async def _recv(self) -> dict | None:
        if not self._process or not self._process.stdout:
            return None
        try:
            line = await self._process.stdout.readline()
            if not line:
                return None
            return json.loads(line.decode("utf-8").strip())
        except Exception as e:
            raise MCPError(f"{_tag(self.name)} 读取消息失败: {e}") from e


__all__ = [
    "MCP_CLIENT_INFO",
    "MCP_PROTOCOL",
    "MCP_SERVERS",
    "MCP_TOOL_CALL_TIMEOUT",
    "MCP_TOOL_PREFIX",
    "MCPServerProcess",
]
