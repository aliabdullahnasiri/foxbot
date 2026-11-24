import pytest
from httpx import ASGITransport, AsyncClient

from bot import main


@pytest.mark.asyncio
async def test_health_is_available_without_telegram_credentials(monkeypatch):
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    async with AsyncClient(
        transport=ASGITransport(app=main()),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health", follow_redirects=False)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
