"""
test_health

为何做：集成测试 health 路由端点，验证 /api/health 和 /api/ping 返回正确

如何测：用 Quart 的 test client，无需启动真实服务

层&依赖：tests.integration 层，依赖 bootstrap.app_factory
"""

import pytest

from flypig.bootstrap.app_factory import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_health_returns_ok(app) -> None:
    test_client = app.test_client()
    response = await test_client.get("/api/health")
    assert response.status_code == 200
    body = await response.get_json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_ping_returns_pong(app) -> None:
    test_client = app.test_client()
    response = await test_client.get("/api/ping")
    assert response.status_code == 200
    body = await response.get_json()
    assert body["pong"] is True
