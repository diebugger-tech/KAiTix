import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Device


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["message"] == "System online"


@pytest.mark.asyncio
async def test_dashboard_stats_endpoint(client: AsyncClient, db: AsyncSession):
    # Add some devices to the test database
    d1 = Device(hostname="test-srv1", typ="server", tdp_watt=350.0)
    d2 = Device(hostname="test-srv2", typ="server", tdp_watt=150.0)
    d3 = Device(hostname="test-sw1", typ="switch", tdp_watt=None)
    db.add_all([d1, d2, d3])
    await db.commit()

    response = await client.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_power_kw" in data
    # 350 + 150 = 500W -> 0.5 kW
    assert data["total_power_kw"] == 0.5
