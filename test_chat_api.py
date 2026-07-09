"""测试 FlyPig chat API 消息格式转换"""
import httpx
import json

def test_chat():
    """用 AI SDK parts 格式发送消息，检验后端是否正确转换"""
    data = {
        "model": "qwen2.5:1.5b",
        "mode": "explore",
        "messages": [
            {
                "parts": [{"type": "text", "text": "用一句话介绍你自己"}],
                "role": "user"
            }
        ]
    }
    
    print("发送请求 (parts格式):", json.dumps(data, ensure_ascii=False))
    
    with httpx.stream(
        'POST',
        'http://localhost:8320/api/chat',
        json=data,
        timeout=30,
    ) as resp:
        print(f"\nStatus: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('content-type')}")
        print("\nSSE 流:")
        for line in resp.iter_lines():
            if not line:
                continue
            if line.startswith('data: '):
                try:
                    msg = json.loads(line[6:])
                    if msg.get('type') == 'text-delta':
                        print(msg.get('delta', ''), end='', flush=True)
                    elif msg.get('type') == 'error':
                        print(f"\n[ERROR] {msg.get('errorText', '')}")
                except json.JSONDecodeError:
                    if '[DONE]' in line:
                        print("\n\n[DONE]")

if __name__ == '__main__':
    test_chat()
