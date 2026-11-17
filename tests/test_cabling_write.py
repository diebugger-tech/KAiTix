from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cable, Device, Rack


async def _create_devices(db: AsyncSession, count: int = 2) -> list[Device]:
    rack = Rack(name="Kabel-Test-Rack", standort="Test")
    db.add(rack)
    await db.flush()
    devices = [
        Device(hostname=f"kabel-test-{index}", typ="server", rack_id=rack.id)
        for index in range(count)
    ]
    db.add_all(devices)
    await db.flush()
    return devices


async def _create_cable(
    client: AsyncClient,
    *,
    kabel_nr: str | None = None,
    typ: str = "Cat6A",
    von_device_id: int | None = None,
    von_port: str | None = None,
    nach_device_id: int | None = None,
    nach_port: str | None = None,
):
    payload = {
        "kabel_nr": kabel_nr,
        "typ": typ,
        "laenge_m": 1,
        "von_device_id": von_device_id,
        "von_port": von_port,
        "nach_device_id": nach_device_id,
        "nach_port": nach_port,
    }
    response = await client.post("/api/v1/cables/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_cable_ports_survive_create_read_update(
    client: AsyncClient, db: AsyncSession
):
    source, target = await _create_devices(db)

    created = await _create_cable(
        client,
        kabel_nr="KAB-0001",
        von_device_id=source.id,
        von_port="eth0",
        nach_device_id=target.id,
        nach_port="Gi1/0/1",
    )
    assert created["von_port"] == "eth0"
    assert created["nach_port"] == "Gi1/0/1"

    read = await client.get(f"/api/v1/cables/{created['id']}")
    assert read.status_code == 200
    assert read.json()["von_port"] == "eth0"
    assert read.json()["nach_port"] == "Gi1/0/1"

    updated = await client.put(
        f"/api/v1/cables/{created['id']}",
        json={"von_port": "eth1", "nach_port": "Gi1/0/2"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["von_port"] == "eth1"
    assert updated.json()["nach_port"] == "Gi1/0/2"

    reread = await client.get(f"/api/v1/cables/{created['id']}")
    assert reread.status_code == 200
    assert reread.json()["von_port"] == "eth1"
    assert reread.json()["nach_port"] == "Gi1/0/2"


async def test_create_rejects_cross_side_port_conflict(
    client: AsyncClient, db: AsyncSession
):
    first, second, third = await _create_devices(db, 3)
    await _create_cable(
        client,
        kabel_nr="KAB-0001",
        von_device_id=first.id,
        von_port="shared",
        nach_device_id=second.id,
        nach_port="eth0",
    )

    response = await client.post(
        "/api/v1/cables/",
        json={
            "kabel_nr": "KAB-0002",
            "typ": "Cat6A",
            "laenge_m": 1,
            "von_device_id": third.id,
            "von_port": "eth0",
            "nach_device_id": first.id,
            "nach_port": "shared",
        },
    )

    assert response.status_code == 409
    assert "KAB-0001" in response.json()["detail"]
    assert "shared" in response.json()["detail"]


async def test_update_rejects_port_conflict(client: AsyncClient, db: AsyncSession):
    first, second, third, fourth = await _create_devices(db, 4)
    await _create_cable(
        client,
        kabel_nr="KAB-0001",
        von_device_id=first.id,
        von_port="occupied",
        nach_device_id=second.id,
        nach_port="eth0",
    )
    other = await _create_cable(
        client,
        kabel_nr="KAB-0002",
        von_device_id=third.id,
        von_port="eth0",
        nach_device_id=fourth.id,
        nach_port="eth1",
    )

    response = await client.put(
        f"/api/v1/cables/{other['id']}",
        json={"von_device_id": first.id, "von_port": "occupied"},
    )

    assert response.status_code == 409
    assert "KAB-0001" in response.json()["detail"]


async def test_power_cables_follow_simulation_conflict_rule(
    client: AsyncClient, db: AsyncSession
):
    first, second, third = await _create_devices(db, 3)
    await _create_cable(
        client,
        kabel_nr="PWR-1",
        typ="Strom-C13",
        von_device_id=first.id,
        von_port="PSU-1",
        nach_device_id=second.id,
        nach_port="Outlet-1",
    )
    duplicate = await _create_cable(
        client,
        kabel_nr="PWR-2",
        typ="Strom-C13",
        von_device_id=third.id,
        von_port="PSU-1",
        nach_device_id=second.id,
        nach_port="Outlet-1",
    )

    assert duplicate["nach_port"] == "Outlet-1"


async def test_generator_uses_highest_kab_number_after_delete(
    client: AsyncClient, db: AsyncSession
):
    for kabel_nr in ["KAB-0001", "KAB-0002", "KAB-0003", "LAN-9999"]:
        await _create_cable(client, kabel_nr=kabel_nr)

    cables = await client.get("/api/v1/cables/")
    deleted_id = next(
        cable["id"] for cable in cables.json() if cable["kabel_nr"] == "KAB-0002"
    )
    deleted = await client.delete(f"/api/v1/cables/{deleted_id}")
    assert deleted.status_code == 204

    generated = await _create_cable(client)

    assert generated["kabel_nr"] == "KAB-0004"


async def test_update_unrelated_field_ignores_legacy_port_conflict(
    client: AsyncClient, db: AsyncSession
):
    first, second, third = await _create_devices(db, 3)
    first_cable = Cable(
        kabel_nr="KAB-ALT-1",
        typ="Cat6A",
        laenge_m=1,
        von_device_id=first.id,
        von_port="shared",
        nach_device_id=second.id,
        nach_port="legacy-shared",
    )
    second_cable = Cable(
        kabel_nr="KAB-ALT-2",
        typ="Cat6A",
        laenge_m=1,
        von_device_id=third.id,
        von_port="other",
        nach_device_id=second.id,
        nach_port="legacy-shared",
    )
    db.add_all([first_cable, second_cable])
    await db.flush()

    updated = await client.put(
        f"/api/v1/cables/{second_cable.id}", json={"farbe": "Blau"}
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["farbe"] == "Blau"

    conflict = await client.put(
        f"/api/v1/cables/{second_cable.id}",
        json={"nach_device_id": first.id, "nach_port": "shared"},
    )
    assert conflict.status_code == 409
    assert "KAB-ALT-1" in conflict.json()["detail"]
    assert "shared" in conflict.json()["detail"]
    assert first.hostname in conflict.json()["detail"]


async def test_generator_extends_beyond_four_digits(
    client: AsyncClient, db: AsyncSession
):
    await _create_cable(client, kabel_nr="KAB-9999")

    first_generated = await _create_cable(client)
    second_generated = await _create_cable(client)

    assert first_generated["kabel_nr"] == "KAB-10000"
    assert second_generated["kabel_nr"] == "KAB-10001"
