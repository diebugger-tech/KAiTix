import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


async def main():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Load the CSV content
        with open("data/eplan_power_import.csv", "rb") as f:
            csv_content = f.read()

        files = {"file": ("eplan_power_import.csv", csv_content, "text/csv")}
        # Empty mapping_json
        data = {"mapping_json": "{}"}

        response = await ac.post("/api/v1/import-eplan/preview", files=files, data=data)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            res_data = response.json()
            print("Preview Stats:")
            print(res_data["stats"])
            print("Parsed Rows (sample):")
            for row in res_data["rows"][:2]:
                print(row)
        else:
            print(response.text)


if __name__ == "__main__":
    asyncio.run(main())
