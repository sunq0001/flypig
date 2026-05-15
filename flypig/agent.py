"""Agent 核心"""
import json
from typing import List, Dict, Optional
from .model import ModelAdapter
from .cost import CostTracker
from .tools import ToolExecutor
from .hooks import EventHook, CostPrintHook


class Agent:
    """Code Agent 核心"""

    def __init__(
        self,
        model: ModelAdapter,
        cost_tracker: CostTracker,
        tools: ToolExecutor,
        system_prompt: str = "",
        hooks: Optional[List[EventHook]] = None
    ):
        self.model = model
        self.cost_tracker = cost_tracker
        self.tools = tools
        self.hooks = hooks or [CostPrintHook()]
        self.messages: List[Dict] = []
        self.verbose = False

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
            response = self.model.chat(
                messages=self.messages,
                tools=self.tools.get_tools_schema()
            )

            # 记录成本
            usage = response["usage"]
            cost_info = self.cost_tracker.record(
                model=self.model.model,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"]
            )

            # ── 后置钩子（含成本打印） ──
            for h in self.hooks:
                h.on_llm_end(usage, cost_info, iteration)

            assistant_content = response["content"]
            self.messages.append({"role": "assistant", "content": assistant_content})

            if self.verbose:
                print(f"[DEBUG] Response ({len(assistant_content)} chars): {assistant_content[:200]}...")
                print(f"[DEBUG] Tool calls: {len(response['tool_calls'])}")

            # 处理工具调用
            if response["tool_calls"]:
                tool_results = []
                for tool_call in response["tool_calls"]:
                    # 工具钩子
                    for h in self.hooks:
                        h.on_tool_start(tool_call["name"], json.loads(tool_call["arguments"]))

                    result = self._execute_tool_call(tool_call)

                    for h in self.hooks:
                        h.on_tool_end(tool_call["name"], result.get("output", ""))

                    tool_results.append(result)

                tool_message = self._format_tool_results(tool_results, response["tool_calls"])
                self.messages.append({"role": "user", "content": tool_message})

                # 检测重复调用模式（含参数，避免不同命令被误判）
                current_calls = tuple(
                    sorted((r['name'], str(r.get('arguments', {}))) for r in tool_results)
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
    
    def _execute_tool_call(self, tool_call: Dict) -> Dict:
        """执行工具调用"""
        name = tool_call["name"]
        arguments = json.loads(tool_call["arguments"])
        
        if self.verbose:
            print(f"[DEBUG] Executing: {name}({json.dumps(arguments)[:100]}...)")
        
        output = self.tools.execute(name, arguments)
        
        return {
            "name": name,
            "arguments": arguments,
            "output": output
        }
    
    def _format_tool_results(self, results: List[Dict], calls: List[Dict]) -> str:
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
    
    def get_session_summary(self) -> str:
        """获取会话汇总"""
        return self.cost_tracker.get_summary()
    
    def reset(self):
        """重置会话"""
        system_msg = self.messages[0] if self.messages and self.messages[0]["role"] == "system" else None
        self.messages = []
        if system_msg:
            self.messages.append(system_msg)
        self.cost_tracker.reset()
