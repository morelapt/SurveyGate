import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio

@pytest.mark.asyncio
async def test_register_twice():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r1 = await ac.post("/bot/users/register", json={"telegram_id": 123456})
        assert r1.status_code == 200
        assert r1.json()["is_new"] is True

        r2 = await ac.post("/bot/users/register", json={"telegram_id": 123456})
        assert r2.status_code == 200
        assert r2.json()["is_new"] is False
