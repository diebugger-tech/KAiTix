import asyncio
import json
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.eplan_parser import EplanParser


async def main():
    # 1. Parse CSV using EplanParser
    with open("data/eplan_power_import.csv", "rb") as f:
        csv_content = f.read()

    default_mapping = {
        "cable_number": "Kabelnummer",
        "cable_type": "Typ",
        "length": "Länge",
        "farbe": "Farbe",
        "source_rack": "Quelle Rack",
        "source_device": "Quelle Gerät",
        "source_port": "Quelle Port",
        "target_rack": "Ziel Rack",
        "target_device": "Ziel Gerät",
        "target_port": "Ziel Port",
    }

    parsed = EplanParser.parse_csv(csv_content, default_mapping)
    print(f"Parsed {len(parsed)} connections from CSV.")

    # 2. Format connections for the ImportCommitRequest payload
    connections = []
    for row in parsed:
        connections.append(
            {
                "cable_number": row.get("cable_number"),
                "cable_type": row.get("cable_type"),
                "length": row.get("length"),
                "farbe": row.get("farbe"),
                "source_rack": row.get("source_rack"),
                "source_device": row.get("source_device"),
                "source_port": row.get("source_port"),
                "target_rack": row.get("target_rack"),
                "target_device": row.get("target_device"),
                "target_port": row.get("target_port"),
            }
        )

    payload = {"connections": connections}

    # 3. Call the commit endpoint
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/import-eplan/commit", json=payload)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 201:
            print("Import Commit Success!")
            print(json.dumps(response.json(), indent=2))
        else:
            print("Error:")
            print(response.text)


if __name__ == "__main__":
    asyncio.run(main())
