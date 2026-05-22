import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from app.models import Rack, Device, DevicePort, Cable


@pytest.mark.asyncio
async def test_export_cables_endpoints(client: AsyncClient, db: AsyncSession):
    # 1. Seed some connection data
    rack_a = Rack(name="Rack A", standort="Lager 1")
    rack_b = Rack(name="Rack B", standort="Lager 2")
    db.add_all([rack_a, rack_b])
    await db.flush()

    dev_a = Device(hostname="Switch A", typ="switch", rack_id=rack_a.id)
    dev_b = Device(hostname="Server B", typ="server", rack_id=rack_b.id)
    db.add_all([dev_a, dev_b])
    await db.flush()

    port_a = DevicePort(device_id=dev_a.id, port_name="Port 1", typ="RJ45")
    port_b = DevicePort(device_id=dev_b.id, port_name="Eth 0", typ="RJ45")
    db.add_all([port_a, port_b])
    await db.flush()

    cable = Cable(
        kabel_nr="W100",
        typ="Cat6",
        laenge_m=Decimal("12.5"),
        farbe="Red",
        von_device_id=dev_a.id,
        von_port="Port 1",
        nach_device_id=dev_b.id,
        nach_port="Eth 0",
    )
    db.add(cable)
    await db.flush()
    port_a.kabel_id = cable.id
    port_b.kabel_id = cable.id
    await db.commit()

    # 2. Test CSV export (ZIP with multiple CSVs)
    response_csv = await client.get("/api/v1/export/csv")
    assert response_csv.status_code == 200
    assert "application/zip" in response_csv.headers["content-type"]
    assert len(response_csv.content) > 0

    # 3. Test XLSX export
    response_xlsx = await client.get("/api/v1/export/xlsx")
    assert response_xlsx.status_code == 200
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in response_xlsx.headers["content-type"]
    )
    assert len(response_xlsx.content) > 0

    # 4. Test ODS export
    response_ods = await client.get("/api/v1/export/ods")
    assert response_ods.status_code == 200
    assert (
        "application/vnd.oasis.opendocument.spreadsheet"
        in response_ods.headers["content-type"]
    )
    assert len(response_ods.content) > 0


@pytest.mark.asyncio
async def test_export_single_endpoints(client: AsyncClient, db: AsyncSession):
    # Seed data
    rack = Rack(name="Rack A", standort="Lager 1")
    db.add(rack)
    await db.flush()

    dev = Device(hostname="Switch A", typ="switch", rack_id=rack.id)
    db.add(dev)
    await db.flush()

    port = DevicePort(device_id=dev.id, port_name="Port 1", typ="RJ45")
    db.add(port)
    await db.flush()

    cable = Cable(
        kabel_nr="W100",
        typ="Cat6",
        laenge_m=Decimal("12.5"),
        farbe="Red",
        von_device_id=dev.id,
        von_port="Port 1",
    )
    db.add(cable)
    await db.flush()
    port.kabel_id = cable.id
    await db.commit()

    # Test single Rack-Inventar exports
    for fmt, mime in [
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("ods", "application/vnd.oasis.opendocument.spreadsheet"),
        ("csv", "text/csv"),
    ]:
        resp = await client.get(f"/api/v1/export/racks?fmt={fmt}")
        assert resp.status_code == 200, f"racks {fmt} failed"
        assert mime in resp.headers["content-type"]
        assert len(resp.content) > 0

    # Test single Ports & Interfaces exports
    for fmt, mime in [
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("ods", "application/vnd.oasis.opendocument.spreadsheet"),
        ("csv", "text/csv"),
    ]:
        resp = await client.get(f"/api/v1/export/interfaces?fmt={fmt}")
        assert resp.status_code == 200, f"interfaces {fmt} failed"
        assert mime in resp.headers["content-type"]
        assert len(resp.content) > 0

    # Test single PDU-Belegung exports
    for fmt, mime in [
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("ods", "application/vnd.oasis.opendocument.spreadsheet"),
        ("csv", "text/csv"),
    ]:
        resp = await client.get(f"/api/v1/export/pdus?fmt={fmt}")
        assert resp.status_code == 200, f"pdus {fmt} failed"
        assert mime in resp.headers["content-type"]
        assert len(resp.content) > 0

    # Test single Cable exports
    for fmt, mime in [
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("ods", "application/vnd.oasis.opendocument.spreadsheet"),
        ("csv", "text/csv"),
    ]:
        resp = await client.get(f"/api/v1/export/cables?fmt={fmt}")
        assert resp.status_code == 200, f"cables {fmt} failed"
        assert mime in resp.headers["content-type"]
        assert len(resp.content) > 0
