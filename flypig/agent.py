"""Agent 核心"""

import json
from pathlib import Path

from .cost import CostTracker
from .hooks import CostPrintHook, EventHook
from .model import ModelAdapter
from .tools import ToolExecutor

# ── 自愈阈值 ──
_SELF_HEAL_THRESHOLD = 3


class Agent:
    """Code Agent 核心"""

    def __init__(
        self,
        model: ModelAdapter,
        cost_tracker: CostTracker,
        tools: ToolExecutor,
        system_prompt: str = "",
        hooks: list[EventHook] | None = None,
    ):
        self.model = model
        self.cost_tracker = cost_tracker
        self.tools = tools
        self.hooks = hooks or [CostPrintHook(workspace_dir=str(self.tools.workspace_dir))]
        self.messages: list[dict] = []
        self.verbose = False

        # ── 自愈相关 ──
        self.error_counter: dict[str, int] = {}  # tool_name → count
        self.heal_history: list[str] = []  # 自愈记录

        # 系统提示
        default_system = """You are FlyPig, a coding assistant.
After using tools, you MUST continue executing until the task is COMPLETE.
Do NOT stop after just finding files - read them and complete the task."""

        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})
        else:
            self.messages.append({"role": "system", "content": default_system})

    def run(self, user_input: str, max_iterations: int = 10) -> str:
        """运行 agent"""
        self.messages.append({"role": "user", "content": user_input})

        iteration = 0
        last_tool_calls = None  # 检测重复调用

        while iteration < max_iterations:
            iteration += 1

            if self.verbose:
                print(f"\n[DEBUG] === Iteration {iteration}/{max_iterations} ===")

            # ── 前置钩子 ──
            for h in self.hooks:
                h.on_llm_start(self.messages, iteration)

            # 调用模型
            response = self.model.chat(messages=self.messages, tools=self.tools.get_tools_schema())

            # 记录成本（含缓存命中统计）
            usage = response["usage"]
            cost_info = self.cost_tracker.record(
                model=self.model.model,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                cache_hit_tokens=usage.get("cache_hit_tokens", 0),
            )

            # ── 后置钩子（含成本打印） ──
            for h in self.hooks:
                h.on_llm_end(usage, cost_info, iteration, model=response.get("model", ""))

            assistant_content = response["content"]
            self.messages.append({"role": "assistant", "content": assistant_content})

            if self.verbose:
                print(
                    f"[DEBUG] Response ({len(assistant_content)} chars): {assistant_content[:200]}..."
                )
                print(f"[DEBUG] Tool calls: {len(response['tool_calls'])}")

            # 处理工具调用
            if response["tool_calls"]:
                # ── 显示 LLM 的思考过程 ──
                thinking = assistant_content.strip()
                if thinking and len(thinking) > 5:
                    # 截断过长思考，保留关键信息
                    if len(thinking) > 180:
                        thinking = thinking[:177] + "..."
                    for h in self.hooks:
                        h.on_thinking(thinking)

                tool_results = []
                for tool_call in response["tool_calls"]:
                    # 工具钩子
                    for h in self.hooks:
                        h.on_tool_start(tool_call["name"], json.loads(tool_call["arguments"]))

                    result = self._execute_tool_call(tool_call)

                    for h in self.hooks:
                        h.on_tool_end(
                            tool_call["name"], result.get("output", ""), result.get("arguments", {})
                        )

                    tool_results.append(result)

                # ── 工具链结束钩子 ──
                for h in self.hooks:
                    h.on_tool_chain_end(tool_results, cost_info, iteration)

                tool_message = self._format_tool_results(tool_results, response["tool_calls"])
                self.messages.append({"role": "user", "content": tool_message})

                # 检测重复调用模式（含参数，避免不同命令被误判）
                current_calls = tuple(
                    sorted((r["name"], str(r.get("arguments", {}))) for r in tool_results)
                )
                if current_calls == last_tool_calls:
                    if self.verbose:
                        print("[DEBUG] Detected repeated tool calls with identical args, stopping.")
                    return "[Agent stopped: repeated tool calls with identical input]"
                last_tool_calls = current_calls

                continue

            # 没有工具调用，检查是否有有效回复
            if assistant_content.strip():
                for h in self.hooks:
                    h.on_response(assistant_content, "")
                return assistant_content

            # 空回复但有内容（比如只是thinking），继续
            if self.verbose:
                print("[DEBUG] Empty response, continuing...")
            continue

        return "Max iterations reached. Task may be incomplete."

    def _self_heal(self, broken_tool: str) -> str:
        """自愈流程：检测工具源码中的常见问题并修复"""

        steps = []

        # 1. 清 __pycache__
        import subprocess
        import sys

        flypig_dir = Path(__file__).parent
        pycache_count = 0
        for pyc in flypig_dir.rglob("__pycache__"):
            try:
                import shutil

                shutil.rmtree(str(pyc))
                pycache_count += 1
            except Exception:
                pass
        steps.append(f"cleared {pycache_count} __pycache__ dir(s)")

        # 2. 读取 tools.py 源码检查常见问题
        tools_py = flypig_dir / "tools.py"
        if tools_py.exists():
            src = tools_py.read_text(encoding="utf-8")

            # 检查 import time 是否在顶层
            tool_bash_func = False
            has_top_level_time = False
            for line in src.split("\n"):
                if line.strip().startswith("def tool_"):
                    tool_bash_func = True
                if tool_bash_func and "import time" in line and line.strip().startswith("import"):
                    has_top_level_time = True
                    break
                if "import time" in line and line.strip().startswith("import"):
                    has_top_level_time = True

            if not has_top_level_time:
                # 在文件顶部添加 import time
                lines = src.split("\n")
                insert_at = 0
                for i, line in enumerate(lines):
                    if line.startswith("import ") or line.startswith("from "):
                        insert_at = i + 1
                lines.insert(insert_at, "import time")
                tools_py.write_text("\n".join(lines), encoding="utf-8")
                steps.append("added missing 'import time' to tools.py")
        else:
            steps.append("tools.py not found, skipping source check")

        # 3. 尝试用 subprocess 验证修复
        try:
            result = subprocess.run(
                [sys.executable, "-c", "from flypig.tools import ToolExecutor; print('OK')"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(flypig_dir.parent),
                check=False,
            )
            if result.returncode == 0:
                steps.append(f"verification passed: {result.stdout.strip()}")
            else:
                steps.append(f"verification failed: {result.stderr.strip()}")
        except Exception as e:
            steps.append(f"verification error: {e}")

        self.heal_history.append(str(steps))
        msg = "[Self-Heal] " + " | ".join(steps)
        if self.verbose:
            print(f"[HEAL] {msg}")
        return msg

    def _execute_tool_call(self, tool_call: dict) -> dict:
        """执行工具调用"""
        name = tool_call["name"]
        arguments = json.loads(tool_call["arguments"])
        arguments = json.loads(tool_call["arguments"])

        if self.verbose:
            print(f"[DEBUG] Executing: {name}({json.dumps(arguments)[:100]}...)")

        output = self.tools.execute(name, arguments)

        # ── 终端交互模式检测（注入不等待）──
        if isinstance(output, str) and output.startswith("[TERMINAL_INJECTED:"):
            # 注入完成后直接返回给 LLM，不阻塞等待
            if self.verbose:
                msg_id = output[19:].rstrip("]").strip()
                print(f"[DEBUG] Terminal injected, msg_id={msg_id}, returning directly")
            # 输出已是自然语言描述，直接传递

        # ── SYSTEM_ERROR 检测 ──
        if isinstance(output, str) and output.startswith("[SYSTEM_ERROR]"):
            self.error_counter[name] = self.error_counter.get(name, 0) + 1
            if self.verbose:
                print(f"[DEBUG] {name} SYSTEM_ERROR #{self.error_counter[name]}")
            if self.error_counter[name] >= _SELF_HEAL_THRESHOLD:
                heal_msg = self._self_heal(name)
                # 插入自愈消息到对话，让 LLM 知道发生了什么
                self.messages.append(
                    {"role": "user", "content": f"<system_heal>\n{heal_msg}\n</system_heal>"}
                )
                self.error_counter[name] = 0
        else:
            # 成功执行 → 重置该工具的计数器
            self.error_counter.pop(name, None)

        return {"name": name, "arguments": arguments, "output": output}

    def _format_tool_results(self, results: list[dict], calls: list[dict]) -> str:
        """格式化工具结果"""
        parts = []
        for i, result in enumerate(results):
            call = calls[i]
            parts.append(
                f"<tool_result>\n"
                f"<tool_name>{result['name']}</tool_name>\n"
                f"<tool_call_id>{call['id']}</tool_call_id>\n"
                f"<result>\n{result['output']}\n</result>\n"
                f"</tool_result>"
            )
        return "\n".join(parts)

    @property
    def bash_history(self) -> list:
        """获取 bash 命令历史（非阻塞记录）"""
        return self.hooks[0].bash_history if self.hooks else []

    def open_terminal(self, index: int = -1):
        """打开终端窗口执行历史中的 bash 命令

        Args:
            index: bash_history 中的索引，-1 表示最后一条
        """
        if self.hooks:
            self.hooks[0].open_terminal(index)

    def get_session_summary(self) -> str:
        """获取会话汇总"""
        return self.cost_tracker.get_summary()

    def reset(self):
        """重置会话"""
        system_msg = (
            self.messages[0] if self.messages and self.messages[0]["role"] == "system" else None
        )
        self.messages = []
        if system_msg:
            self.messages.append(system_msg)
        self.cost_tracker.reset()
