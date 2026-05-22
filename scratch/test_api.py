import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


async def test_device():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/devices/",
            json={
                "hostname": "7",
                "typ": "server",
                "rack_id": 1,
                "u_position": 16,
                "u_hoehe": 1,
                "phase": "L1",
                "anschlussleistung_watt": 250,
            },
        )
        print(response.status_code)
        print(response.json())


if __name__ == "__main__":
    asyncio.run(test_device())
