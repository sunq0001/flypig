"""测试 Ollama 流式 API"""
import httpx
import json

def test_stream():
    with httpx.stream(
        'POST',
        'http://localhost:11434/v1/chat/completions',
        json={
            'model': 'qwen2.5:1.5b',
            'messages': [{'role': 'user', 'content': '你好，用一句话介绍你自己'}],
            'stream': True,
            'max_tokens': 100,
        },
        timeout=30,
    ) as resp:
        print(f"Status: {resp.status_code}")
        for line in resp.iter_lines():
            if not line or not line.startswith('data:'):
                continue
            if line == 'data: [DONE]':
                print("\n[DONE]")
                break
            try:
                data = json.loads(line.replace('data: ', '', 1))
                content = data['choices'][0]['delta'].get('content', '')
                if content:
                    print(content, end='', flush=True)
            except Exception:
                pass

if __name__ == '__main__':
    test_stream()
