"""测试 FlyPig chat API — 直接用 content 格式"""
import json
import httpx

def test_with_content_format():
    """用 OpenAI 标准 content 格式（已转换过的）"""
    data = {
        "model": "qwen2.5:1.5b",
        "mode": "explore",
        "messages": [
            {"role": "user", "content": "用一句话介绍你自己"}
        ]
    }
    
    print("发送请求 (content格式):", json.dumps(data, ensure_ascii=False))
    
    with httpx.stream('POST', 'http://localhost:8320/api/chat', json=data, timeout=30) as resp:
        print(f"\nStatus: {resp.status_code}")
        print("\nSSE 流:")
        for line in resp.iter_lines():
            if not line:
                continue
            if line.startswith('data: '):
                payload = line[6:]
                try:
                    msg = json.loads(payload)
                    if msg.get('type') == 'text-delta':
                        print(msg.get('delta', ''), end='', flush=True)
                    elif msg.get('type') == 'error':
                        print(f"\n[ERROR] {msg.get('errorText', '')}")
                    elif msg.get('type') in ('text-start', 'text-end', 'finish'):
                        print(f"\n[{msg['type']}]", end='')
                except json.JSONDecodeError:
                    if '[DONE]' in payload:
                        print("\n[DONE]")

if __name__ == '__main__':
    test_with_content_format()
