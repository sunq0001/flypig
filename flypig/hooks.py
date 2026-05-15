"""Agent 生命周期钩子 (Hook) 系统

用法:
    from flypig.hooks import EventHook, CostPrintHook

    agent = Agent(..., hooks=[CostPrintHook()])

自定义:
    class MyHook(EventHook):
        def on_llm_end(self, usage, cost_info, iteration):
            send_to_telemetry(usage)
"""


class EventHook:
    """Agent 生命周期钩子基类 — 所有方法都是空实现，子类按需覆盖"""

    def on_llm_start(self, messages: list, iteration: int):
        """LLM 调用前触发"""

    def on_llm_end(self, usage: dict, cost_info: dict, iteration: int):
        """LLM 调用后触发"""

    def on_tool_start(self, tool_name: str, arguments: dict):
        """工具执行前触发"""

    def on_tool_end(self, tool_name: str, result: str):
        """工具执行后触发"""

    def on_response(self, content: str, usage_line: str):
        """Agent 返回最终回复时触发"""


class CostPrintHook(EventHook):
    """默认钩子：每次 LLM 返回时打印 token 用量到控制台"""

    def on_llm_end(self, usage: dict, cost_info: dict, iteration: int):
        total = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        cost = cost_info.get("cost", 0)
        from .cost import _format_cost
        print(f"[Tokens: {total:,}] [Cost: {_format_cost(cost)}]")

    def on_tool_start(self, tool_name: str, arguments: dict):
        """工具调用前打印：显示关键参数"""
        if tool_name == "bash":
            cmd = arguments.get("command", "")
            display = cmd[:120] + ("..." if len(cmd) > 120 else "")
            print(f"[>] bash: {display}")
        elif tool_name in ("read_file", "write_file", "edit_file"):
            path = arguments.get("path", "")
            print(f"[>] {tool_name}: {path}")
        elif tool_name == "find_files":
            pattern = arguments.get("pattern", "")
            print(f"[>] find: {pattern}")
        elif tool_name == "grep":
            pattern = arguments.get("pattern", "")
            print(f"[>] grep: {pattern}")
        else:
            print(f"[>] {tool_name}")

    def on_tool_end(self, tool_name: str, result: str):
        """工具执行后打印输出（仅截取非 bash 工具的简要结果）"""
        if tool_name == "bash":
            # bash 输出可能很长，只打印非空且不太长的响应
            lines = result.strip().split("\n")
            if len(lines) <= 5 and all(len(l) < 200 for l in lines):
                for l in lines:
                    print(f"  {l}")
            elif lines and lines[0]:
                print(f"  {lines[0]}")
                if len(lines) > 1:
                    print(f"  ... ({len(result)} chars)")


# 未来扩展的钩子可以加在这里，或者单独文件
# class AuditLogHook(EventHook): ...
# class DebugTraceHook(EventHook): ...
# class TelemetryHook(EventHook): ...

