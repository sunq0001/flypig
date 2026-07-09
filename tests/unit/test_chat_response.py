"""
test_chat_response

为何做：测试 application/dto/chat_response.py 的 ChatResponse DTO

如何测：
- 各工厂方法（text_delta / text_start / text_end / finish / error）输出正确字段
- to_sse() 序列化为正确的 SSE 格式
- metadata 字段合并到 payload

层&依赖：tests.unit 层，依赖 application.dto.chat_response
"""

import json

from flypig.application.dto.chat_response import ChatResponse


class TestChatResponseFactory:
    """ChatResponse 工厂方法测试"""

    def test_text_delta(self) -> None:
        r = ChatResponse.text_delta("hello")
        assert r.type == "text-delta"
        assert r.content == "hello"

    def test_text_start(self) -> None:
        r = ChatResponse.text_start()
        assert r.type == "text-start"
        assert r.content == ""

    def test_text_end(self) -> None:
        r = ChatResponse.text_end()
        assert r.type == "text-end"
        assert r.content == ""

    def test_finish(self) -> None:
        r = ChatResponse.finish()
        assert r.type == "finish"
        assert r.content is None

    def test_error(self) -> None:
        r = ChatResponse.error("something went wrong")
        assert r.type == "error"
        assert r.content == "something went wrong"


class TestChatResponseSSE:
    """ChatResponse SSE 序列化测试"""

    def test_text_delta_sse(self) -> None:
        r = ChatResponse.text_delta("hello")
        data = json.loads(r.to_sse()[len("data: ") :].strip())
        assert data == {"type": "text-delta", "delta": "hello"}

    def test_text_start_sse(self) -> None:
        r = ChatResponse.text_start()
        data = json.loads(r.to_sse()[len("data: ") :].strip())
        assert data == {"type": "text-start", "delta": ""}

    def test_finish_sse(self) -> None:
        r = ChatResponse.finish()
        data = json.loads(r.to_sse()[len("data: ") :].strip())
        assert data == {"type": "finish"}

    def test_error_sse(self) -> None:
        r = ChatResponse.error("err")
        data = json.loads(r.to_sse()[len("data: ") :].strip())
        assert data == {"type": "error", "content": "err"}

    def test_sse_ends_with_double_newline(self) -> None:
        r = ChatResponse.finish()
        assert r.to_sse().endswith("\n\n")

    def test_sse_prefix(self) -> None:
        r = ChatResponse.finish()
        assert r.to_sse().startswith("data: ")

    def test_metadata_merged(self) -> None:
        r = ChatResponse(type="finish", metadata={"usage": 100})
        data = json.loads(r.to_sse()[len("data: ") :].strip())
        assert data == {"type": "finish", "usage": 100}

    def test_chinese_content(self) -> None:
        r = ChatResponse.text_delta("你好世界")
        assert b'"hello"' not in r.to_sse().encode()
        data = json.loads(r.to_sse()[len("data: ") :].strip())
        assert data == {"type": "text-delta", "delta": "你好世界"}
