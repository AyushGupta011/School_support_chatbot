import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check_returns_correct_format():
    # In a real test, we would mock DB/Redis or rely on test containers
    # For phase 0, we're just checking the endpoint structure
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "postgres" in data
        assert "redis" in data
