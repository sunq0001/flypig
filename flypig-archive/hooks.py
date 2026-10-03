"""Agent 生命周期钩子 (Hook) 系统

用法:
    from flypig.hooks import EventHook, CostPrintHook

    agent = Agent(..., hooks=[CostPrintHook()])

自定义:
    class MyHook(EventHook):
        def on_llm_end(self, usage, cost_info, iteration):
            send_to_telemetry(usage)
"""

import asyncio
import os


# ── 工具中文说明 ──
_TOOL_DESCRIPTION = {
    "bash": "\u8fd0\u884c\u547d\u4ee4",  # 运行命令
    "read_file": "\u8bfb\u53d6\u6587\u4ef6",  # 读取文件
    "write_file": "\u5199\u5165\u6587\u4ef6",  # 写入文件
    "edit_file": "\u7f16\u8f91\u6587\u4ef6",  # 编辑文件
    "find_files": "\u67e5\u627e\u6587\u4ef6",  # 查找文件
    "grep": "\u641c\u7d22\u5185\u5bb9",  # 搜索内容
}


# ── 工具参数摘要提取（控制在 50 字以内） ──
def _summarize_args(tool_name: str, arguments: dict) -> str:
    """提取关键参数作为说明文字"""
    if tool_name == "bash":
        cmd = arguments.get("command", "")
        # 截取核心命令
        return cmd[:90] + ("..." if len(cmd) > 90 else "")
    elif tool_name in ("read_file", "write_file", "edit_file"):
        return arguments.get("path", "")
    elif tool_name == "find_files":
        return f"pattern={arguments.get('pattern', '*')}"
    elif tool_name == "grep":
        return f"'{arguments.get('pattern', '')[:40]}'"
    return ""


class EventHook:
    """Agent 生命周期钩子基类 — 所有方法都是空实现，子类按需覆盖"""

    def on_llm_start(self, messages: list, iteration: int):
        """LLM 调用前触发"""

    def on_llm_end(self, usage: dict, cost_info: dict, iteration: int, model: str = ""):
        """LLM 调用后触发"""

    def on_tool_start(self, tool_name: str, arguments: dict):
        """工具执行前触发"""

    def on_tool_end(self, tool_name: str, result: str, arguments: dict = None):
        """工具执行后触发"""

    def on_tool_chain_end(self, tool_results: list, cost_info: dict, iteration: int):
        """当前迭代的所有工具调用执行完毕后触发"""

    def on_response(self, content: str, usage_line: str):
        """Agent 返回最终回复时触发"""

    def on_thinking(self, content: str):
        """Agent 思考过程（LLM 返回内容但尚未开始工具调用时触发）"""


class CostPrintHook(EventHook):
    """默认钩子：每次 LLM 返回时打印 token 用量 + 工具链可视化"""

    def __init__(self, workspace_dir: str = None):
        # 会话级累计
        self.session_tokens = 0
        self.session_cost = 0.0
        self.session_tools = 0
        self.workspace_dir = workspace_dir
        self.bash_history: list = []  # bash 命令历史（非阻塞记录）

    def on_llm_end(self, usage: dict, cost_info: dict, iteration: int, model: str = ""):
        total = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        cost = cost_info.get("cost", 0)
        self.session_tokens += total
        self.session_cost += cost
        from .cost import _format_cost

        model_tag = f" [{model}]" if model else ""
        # 缓存命中显示
        hit = usage.get("cache_hit_tokens", 0)
        inp = usage.get("input_tokens", 0)
        cache_tag = ""
        if hit and inp:
            pct = 100 * hit / inp
            cache_tag = f" [Cache: {pct:.0f}% hit]"
        print(f"[Tokens: {total:,}]{model_tag}{cache_tag} [Cost: {_format_cost(cost)}]")

    def on_thinking(self, content: str):
        print(f"  [思考] {content}")

    def on_tool_start(self, tool_name: str, arguments: dict):
        """工具调用前打印：带中文说明"""
        desc = _TOOL_DESCRIPTION.get(tool_name, tool_name)
        summary = _summarize_args(tool_name, arguments)
        if summary:
            print(f"  [>] {desc}: {summary}")
        else:
            print(f"  [>] {desc}")

    def on_tool_end(self, tool_name: str, result: str, arguments: dict = None):
        """工具执行后打印输出，bash 命令额外提供打开交互终端选项"""
        lines = result.strip().split("\n")
        if len(lines) <= 3 and all(len(l) < 200 for l in lines):
            for l in lines:
                if l:
                    print(f"    {l}")
        elif lines and lines[0]:
            first = lines[0][:120]
            print(f"    {first}")
            if len(lines) > 1:
                print(f"    ... ({len(result)} chars)")

        # ── bash 命令 → 非阻塞记录历史 + 提示 ──
        if tool_name == "bash" and arguments:
            cmd = arguments.get("command", "")
            persist = arguments.get("persist", False)
            if cmd and not persist:
                self.bash_history.append(cmd)
                idx = len(self.bash_history)
                print(f"  [T] 输入 t 打开终端 (#{idx} 条)")

    def open_terminal(self, index=-1):
        """在控制台中打印历史命令（不再弹独立窗口）

        Args:
            index: 在 bash_history 中的索引，-1 表示最后一条
        """
        if not self.bash_history:
            print("  [X] 没有可用的终端历史")
            return

        try:
            command = self.bash_history[index]
        except IndexError:
            print(f"  [X] 无效的序号，历史命令共 {len(self.bash_history)} 条")
            return

        print(f"\n{'=' * 50}")
        print(f"  [终端 #{index + 1}] 命令:")
        print(f"  {command}")
        print(f"  工作目录: {self.workspace_dir or os.getcwd()}")
        print("  [*] 请复制命令到终端中执行")
        print(f"{'=' * 50}")

    def on_tool_chain_end(self, tool_results: list, cost_info: dict, iteration: int):
        """当前迭代的工具链结束后打印累计"""
        tool_count = len(tool_results)
        self.session_tools += tool_count
        total_tokens = cost_info.get("input_tokens", 0) + cost_info.get(
            "output_tokens", 0
        )
        cost = cost_info.get("cost", 0)
        from .cost import _format_cost

        print(
            f"  [Chain: {tool_count} tools, Tokens: {total_tokens:,}, Cost: {_format_cost(cost)}]"
        )

    def on_response(self, content: str, usage_line: str):
        """Agent 返回最终回复时打印会话累计"""
        from .cost import _format_cost

        print(
            f"[Done] Tools: {self.session_tools}, Total Tokens: {self.session_tokens:,}, Total Cost: {_format_cost(self.session_cost)}"
        )


class WsEventHook(EventHook):
    """WebSocket 事件钩子：将 Agent 事件广播到所有 WS 客户端

    用法：
        hook = WsEventHook()
        hook.set_loop(asyncio.get_event_loop())
        hook.set_broadcaster(ws_broadcast_func)  # async function(data: dict)
        agent = Agent(..., hooks=[hook])
    """

    def __init__(self):
        self._loop = None
        self._broadcast_func = None
        self.session_tokens = 0
        self.session_cost = 0.0
        self.session_tools = 0
        self.bash_history: list = []

    def set_loop(self, loop):
        self._loop = loop

    def set_broadcaster(self, broadcast_func):
        """注册 async broadcast 函数（由 server.py 提供）"""
        self._broadcast_func = broadcast_func

    def _broadcast(self, data: dict):
        """线程安全地广播事件到所有 WS 客户端

        使用 run_coroutine_threadsafe 将协程调度到主事件循环
        """
        if not self._broadcast_func or not self._loop or self._loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(self._broadcast_func(data), self._loop)
        except RuntimeError:
            pass

    def on_thinking(self, content: str):
        self._broadcast({"type": "thinking", "content": content})

    def on_tool_start(self, tool_name: str, arguments: dict):
        self._broadcast(
            {
                "type": "tool_call",
                "name": tool_name,
                "args": arguments,
            }
        )

    def on_tool_end(self, tool_name: str, result: str, arguments: dict = None):
        truncated = result[:3000] if result else ""
        self._broadcast(
            {
                "type": "tool_result",
                "name": tool_name,
                "result": truncated,
                "args": arguments or {},
            }
        )
        if tool_name == "bash" and arguments:
            cmd = arguments.get("command", "")
            if cmd:
                self.bash_history.append(cmd)

    def on_llm_end(self, usage: dict, cost_info: dict, iteration: int, model: str = ""):
        total = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        cost = cost_info.get("cost", 0)
        self.session_tokens += total
        self.session_cost += cost
        hit = usage.get("cache_hit_tokens", 0)
        inp = usage.get("input_tokens", 0)
        self._broadcast(
            {
                "type": "llm_end",
                "model": model,
                "tokens": total,
                "input_tokens": inp,
                "output_tokens": usage.get("output_tokens", 0),
                "cache_hit_tokens": hit,
                "cache_pct": round(100 * hit / inp, 0) if inp and hit else 0,
                "cost": cost,
                "session_tokens": self.session_tokens,
                "session_cost": self.session_cost,
            }
        )

    def on_tool_chain_end(self, tool_results: list, cost_info: dict, iteration: int):
        self._broadcast(
            {
                "type": "tool_chain_end",
                "tool_count": len(tool_results),
                "tokens": cost_info.get("input_tokens", 0)
                + cost_info.get("output_tokens", 0),
                "cost": cost_info.get("cost", 0),
            }
        )

    def on_response(self, content: str, usage_line: str):
        self._broadcast({"type": "response", "content": content})


# 未来扩展的钩子可以加在这里，或者单独文件
# class AuditLogHook(EventHook): ...
# class DebugTraceHook(EventHook): ...
# class TelemetryHook(EventHook): ...
