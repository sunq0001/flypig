"""DeepSeek API 适配"""
from openai import OpenAI
from typing import List, Dict, Optional


class ModelAdapter:
    """统一模型接口，支持 DeepSeek/OpenAI"""
    
    def __init__(self, config: dict):
        self.config = config
        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=config.get("base_url", "https://api.deepseek.com")
        )
        self.model = config.get("model", "deepseek-chat")
    
    def chat(self, messages: List[Dict], tools: List[Dict] = None) -> Dict:
        """
        发送聊天请求
        
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
        
        response = self.client.chat.completions.create(**params)
        
        choice = response.choices[0]
        
        result = {
            "content": choice.message.content or "",
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "tool_calls": []
        }
        
        # 处理工具调用
        if choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                result["tool_calls"].append({
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                })
        
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
