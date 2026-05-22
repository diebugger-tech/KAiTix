import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Rack, Device, DevicePort, Cable


@pytest.mark.asyncio
async def test_eplan_preview_and_commit(client: AsyncClient, db: AsyncSession):
    # 1. Prepare CSV file contents
    csv_data = (
        "Kabelnummer;Typ;Länge;Farbe;Quelle Rack;Quelle Gerät;Quelle Port;Ziel Rack;Ziel Gerät;Ziel Port\n"
        "W101;Cat6;15,5;Blau;Rack A;Switch01;Port 1;Rack B;Server01;Eth0\n"
        "W102;LWL-LC;50;Gelb;Rack A;Patchpanel;Port 12;Rack C;CoreSwitch;Port A1\n"
    )

    mapping = {
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

    # 2. Call preview endpoint
    files = {"file": ("eplan.csv", csv_data.encode("utf-8"), "text/csv")}
    data = {"mapping_json": json.dumps(mapping)}

    response = await client.post("/api/v1/import-eplan/preview", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()

    assert res_data["stats"]["total_rows"] == 2
    assert res_data["stats"]["new_cables"] == 2
    assert res_data["stats"]["missing_racks_count"] == 3  # Rack A, Rack B, Rack C
    assert (
        res_data["stats"]["missing_devices_count"] == 4
    )  # Switch01, Server01, Patchpanel, CoreSwitch

    # Verify the first row parsed values
    first_row = res_data["rows"][0]
    assert first_row["cable_number"] == "W101"
    assert first_row["cable_type"] == "Cat6"
    assert first_row["length"] == 15.5
    assert first_row["source"]["rack"] == "Rack A"
    assert first_row["source"]["device"] == "Switch01"
    assert first_row["source"]["port"] == "Port 1"

    # 3. Call commit endpoint
    # Extract row info to import
    import_payload = {
        "connections": [
            {
                "cable_number": r["cable_number"],
                "cable_type": r["cable_type"],
                "length": r["length"],
                "farbe": r["farbe"],
                "source_rack": r["source"]["rack"],
                "source_device": r["source"]["device"],
                "source_port": r["source"]["port"],
                "target_rack": r["target"]["rack"],
                "target_device": r["target"]["device"],
                "target_port": r["target"]["port"],
            }
            for r in res_data["rows"]
        ]
    }

    response_commit = await client.post(
        "/api/v1/import-eplan/commit", json=import_payload
    )
    assert response_commit.status_code == 201
    commit_res = response_commit.json()
    assert commit_res["imported_cables"] == 2
    assert commit_res["created_racks"] == 3
    assert commit_res["created_devices"] == 4

    # 4. Check DB entries are created
    r_query = await db.execute(select(Rack).where(Rack.name == "Rack A"))
    rack_a = r_query.scalar_one_or_none()
    assert rack_a is not None
    assert rack_a.standort == "Imported"

    d_query = await db.execute(select(Device).where(Device.hostname == "Server01"))
    server = d_query.scalar_one_or_none()
    assert server is not None

    c_query = await db.execute(select(Cable).where(Cable.kabel_nr == "W102"))
    cable_lwl = c_query.scalar_one_or_none()
    assert cable_lwl is not None
    assert cable_lwl.typ == "LC-LC"
    assert float(cable_lwl.laenge_m) == 50.0

    # Verify port was auto-created as Fiber (LC) due to matching keyword in cable type
    p_query = await db.execute(
        select(DevicePort).where(DevicePort.device_id == server.id)
    )
    port = p_query.scalar_one_or_none()
    assert port is not None
    assert port.port_name == "Eth0"
    assert port.typ == "RJ45"  # Cat6 default
