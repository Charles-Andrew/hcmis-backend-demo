import anyio
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _health_request():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.get("/health")


def test_health_endpoint():
    response = anyio.run(_health_request)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
