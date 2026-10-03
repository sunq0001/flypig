"""DeepSeek API 适配"""

from openai import OpenAI
from typing import List, Dict


class ModelAdapter:
    """统一模型接口，支持 DeepSeek/OpenAI"""

    def __init__(self, config: dict):
        self.config = config
        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=config.get("base_url", "https://api.deepseek.com"),
            timeout=120,  # HTTP 请求超时，防止第二次请求卡死
            max_retries=2,  # 网络波动自动重试
        )
        self.model = config.get("model", "deepseek-v4-flash")

    def chat(self, messages: List[Dict], tools: List[Dict] = None) -> Dict:
        """
        发送聊天请求，HTTP 异常/超时时返回空响应（不让 agent 循环卡死）

        Returns:
            {
                "content": str,  # 回复内容
                "usage": {       # token 使用情况
                    "input_tokens": int,
                    "output_tokens": int,
                    "total_tokens": int
                },
                "tool_calls": []  # 工具调用 (如果有)
            }
        """
        params = {
            "model": self.model,
            "messages": messages,
        }

        if tools:
            params["tools"] = tools

        try:
            response = self.client.chat.completions.create(**params)
        except Exception as e:
            # HTTP 超时/网络异常 → 返回空响应，agent 循环不会卡死
            return {
                "content": f"[API Error] {type(e).__name__}: {e}",
                "model": self.model,
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cache_hit_tokens": 0,
                },
                "tool_calls": [],
            }

        choice = response.choices[0]

        result = {
            "content": choice.message.content or "",
            "model": response.model,  # DeepSeek API 返回的真实模型名
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "cache_hit_tokens": getattr(
                    getattr(response.usage, "prompt_tokens_details", None),
                    "cached_tokens",
                    0,
                )
                or 0,
            },
            "tool_calls": [],
        }

        # 处理工具调用
        if choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                result["tool_calls"].append(
                    {
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    }
                )

        return result

    def chat_stream(self, messages: List[Dict], tools: List[Dict] = None):
        """流式聊天"""
        params = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

        if tools:
            params["tools"] = tools

        return self.client.chat.completions.create(**params)
