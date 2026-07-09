"""Test AI SDK parts format after fix"""
import httpx

data = {
    'model': 'qwen2.5:1.5b',
    'mode': 'explore',
    'messages': [{'parts': [{'type': 'text', 'text': '1+1 equals what'}], 'role': 'user'}]
}
print('=== AI SDK parts format ===')
with httpx.stream('POST', 'http://localhost:8320/api/chat', json=data, timeout=60) as resp:
    result = []
    for line in resp.iter_lines():
        if line:
            result.append(line)
            print(line)
    delta_count = sum(1 for l in result if 'text-delta' in l)
    print(f'Delta count: {delta_count}')
