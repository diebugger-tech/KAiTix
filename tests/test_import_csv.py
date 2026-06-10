import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Device, Cable


@pytest.mark.asyncio
async def test_csv_import_db_duplicate_no_update(client: AsyncClient, db: AsyncSession):
    # Setup: Create a device
    dev = Device(hostname="db-dup-test", typ="server", rack_id=None, u_hoehe=1)
    db.add(dev)
    await db.commit()

    # Try to import same hostname with update_mode=False
    payload = {
        "rows": [{"row": 1, "hostname": "db-dup-test", "typ": "server"}],
        "update_mode": False,
    }
    resp = await client.post("/api/v1/import-csv/devices/commit", json=payload)

    assert resp.status_code == 400
    data = resp.json()
    assert "conflicts" in data["detail"]
    assert len(data["detail"]["conflicts"]["db_duplicates"]) == 1
    assert "db-dup-test" in data["detail"]["conflicts"]["db_duplicates"][0]


@pytest.mark.asyncio
async def test_csv_import_intra_csv_duplicate(client: AsyncClient, db: AsyncSession):
    # Try to import same hostname twice in the same batch
    payload = {
        "rows": [
            {"row": 1, "hostname": "intra-dup-test", "typ": "server"},
            {"row": 2, "hostname": "intra-dup-test", "typ": "server"},
        ],
        "update_mode": False,
    }
    resp = await client.post("/api/v1/import-csv/devices/commit", json=payload)

    assert resp.status_code == 400
    data = resp.json()
    assert len(data["detail"]["conflicts"]["csv_duplicates"]) == 1
    assert "intra-dup-test" in data["detail"]["conflicts"]["csv_duplicates"][0]


@pytest.mark.asyncio
async def test_csv_import_clean(client: AsyncClient, db: AsyncSession):
    # Clean import
    payload = {
        "rows": [
            {"row": 1, "hostname": "clean-test-1", "typ": "server"},
            {"row": 2, "hostname": "clean-test-2", "typ": "switch"},
        ],
        "update_mode": False,
    }
    resp = await client.post("/api/v1/import-csv/devices/commit", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 2
    assert data["updated"] == 0

    # Verify in DB
    dev1 = (
        await db.execute(select(Device).where(Device.hostname == "clean-test-1"))
    ).scalar_one_or_none()
    assert dev1 is not None


@pytest.mark.asyncio
async def test_csv_import_update_mode_unknown_key(
    client: AsyncClient, db: AsyncSession
):
    # update_mode=True but key is unknown -> Should insert!
    payload = {
        "rows": [{"row": 1, "hostname": "update-unknown-test", "typ": "server"}],
        "update_mode": True,
    }
    resp = await client.post("/api/v1/import-csv/devices/commit", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 1
    assert data["updated"] == 0

    dev = (
        await db.execute(select(Device).where(Device.hostname == "update-unknown-test"))
    ).scalar_one_or_none()
    assert dev is not None


@pytest.mark.asyncio
async def test_csv_import_cables_empty_kabel_nr(client: AsyncClient, db: AsyncSession):
    # Two cables without kabel_nr -> Should both be inserted without conflicts
    payload = {
        "rows": [
            {"row": 1, "kabel_nr": "", "typ": "LWL", "laenge_m": 5.0},
            {"row": 2, "kabel_nr": None, "typ": "CAT6", "laenge_m": 2.0},
        ],
        "update_mode": False,
    }
    resp = await client.post("/api/v1/import-csv/cables/commit", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 2

    # Verify both are None in DB and not empty strings or UUIDs
    cables = (
        (await db.execute(select(Cable).where(Cable.laenge_m.in_([5.0, 2.0]))))
        .scalars()
        .all()
    )
    assert len(cables) == 2
    assert cables[0].kabel_nr is None
    assert cables[1].kabel_nr is None


@pytest.mark.asyncio
async def test_csv_import_rack_collisions(client: AsyncClient, db: AsyncSession):
    from app.models import Rack

    rack = Rack(name="R1", standort="standort", hoehe_u=42)
    db.add(rack)
    await db.commit()
    await db.refresh(rack)
    rack_id = rack.id

    dev = Device(
        hostname="server-01", typ="server", rack_id=rack_id, u_position=10, u_hoehe=2
    )
    db.add(dev)
    await db.commit()

    # 1. Test collision with existing device
    payload1 = {
        "rows": [
            {
                "row": 1,
                "hostname": "server-02",
                "typ": "server",
                "rack_id": rack_id,
                "u_position": 11,
                "u_hoehe": 1,
            }
        ],
        "update_mode": False,
    }
    resp1 = await client.post("/api/v1/import-csv/devices/commit", json=payload1)
    assert resp1.status_code == 400
    data1 = resp1.json()
    assert len(data1["detail"]["conflicts"]["rack_collisions"]) == 1
    assert "server-02" in data1["detail"]["conflicts"]["rack_collisions"][0]
    assert "server-01" in data1["detail"]["conflicts"]["rack_collisions"][0]

    # 2. Test intra-csv collision
    payload2 = {
        "rows": [
            {
                "row": 1,
                "hostname": "server-03",
                "typ": "server",
                "rack_id": rack_id,
                "u_position": 20,
                "u_hoehe": 4,
            },
            {
                "row": 2,
                "hostname": "server-04",
                "typ": "server",
                "rack_id": rack_id,
                "u_position": 23,
                "u_hoehe": 1,
            },
        ],
        "update_mode": False,
    }
    resp2 = await client.post("/api/v1/import-csv/devices/commit", json=payload2)
    assert resp2.status_code == 400
    data2 = resp2.json()
    assert len(data2["detail"]["conflicts"]["rack_collisions"]) == 1
    assert "server-04" in data2["detail"]["conflicts"]["rack_collisions"][0]
    assert "server-03" in data2["detail"]["conflicts"]["rack_collisions"][0]


@pytest.mark.asyncio
async def test_csv_import_rack_no_collision_stacked(
    client: AsyncClient, db: AsyncSession
):
    from app.models import Rack

    rack = Rack(name="R2", standort="standort", hoehe_u=42)
    db.add(rack)
    await db.commit()
    await db.refresh(rack)
    rack_id = rack.id

    dev = Device(
        hostname="stack-01", typ="server", rack_id=rack_id, u_position=10, u_hoehe=2
    )
    db.add(dev)
    await db.commit()

    # Test stacked device (U10 height 2 = U10-U11, next is U12)
    # Also test Zero-U device (u_hoehe=0)
    payload = {
        "rows": [
            {
                "row": 1,
                "hostname": "stack-02",
                "typ": "server",
                "rack_id": rack_id,
                "u_position": 12,
                "u_hoehe": 1,
            },
            {
                "row": 2,
                "hostname": "zero-u-1",
                "typ": "pdu",
                "rack_id": rack_id,
                "u_position": 10,
                "u_hoehe": 0,
            },
            {
                "row": 3,
                "hostname": "zero-u-2",
                "typ": "pdu",
                "rack_id": rack_id,
                "u_position": 10,
                "u_hoehe": 0,
            },
        ],
        "update_mode": False,
    }
    resp = await client.post("/api/v1/import-csv/devices/commit", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 3
