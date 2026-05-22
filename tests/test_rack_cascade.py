import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import (
    Rack,
    UsvUnit,
    Device,
    PduOutlet,
    ServerInterface,
    DevicePort,
    Cable,
    CableStrand,
)


@pytest.mark.asyncio
async def test_rack_delete_cascade(db: AsyncSession):
    # 1. Setup entities
    rack = Rack(name="Cascade Test Rack", standort="Room B", hoehe_u=42)
    db.add(rack)
    await db.flush()

    usv = UsvUnit(bezeichnung="Test USV Cascade", rack_id=rack.id, max_kw=Decimal("10"))
    db.add(usv)
    await db.flush()

    device = Device(
        hostname="test-srv",
        typ="server",
        rack_id=rack.id,
        phase="L1",
        tdp_watt=Decimal("500"),
    )
    db.add(device)
    await db.flush()

    # Add dependent entities
    outlet = PduOutlet(
        pdu_id=device.id,
        outlet_name="PDU Port 1",
        phase="L1",
        steckdosentyp="C13",
    )
    db.add(outlet)

    interface = ServerInterface(device_id=device.id, port_name="eth0", typ="1GbE")
    db.add(interface)

    port = DevicePort(device_id=device.id, port_name="port1", typ="RJ45")
    db.add(port)
    await db.flush()

    # Create Cable connecting to the port
    cable = Cable(
        kabel_nr="CABLE-TEST-01",
        typ="Cat6",
        laenge_m=Decimal("2.0"),
        von_device_id=device.id,
        von_port="port1",
    )
    db.add(cable)
    await db.flush()

    # Create CableStrand linking to the port
    strand = CableStrand(
        cable_id=cable.id,
        strand_number=1,
        von_port_id=port.id,
    )
    db.add(strand)
    await db.commit()

    # 2. Perform Rack deletion
    await db.delete(rack)
    await db.commit()

    # 3. Assertions - check if rack and everything cascaded from it was deleted
    # Rack should be gone
    res = await db.execute(select(Rack).where(Rack.id == rack.id))
    assert res.scalar_one_or_none() is None

    # UsvUnit should be gone
    res = await db.execute(select(UsvUnit).where(UsvUnit.id == usv.id))
    assert res.scalar_one_or_none() is None

    # Device should be gone
    res = await db.execute(select(Device).where(Device.id == device.id))
    assert res.scalar_one_or_none() is None

    # ServerInterface should be gone
    res = await db.execute(
        select(ServerInterface).where(ServerInterface.id == interface.id)
    )
    assert res.scalar_one_or_none() is None

    # DevicePort should be gone
    res = await db.execute(select(DevicePort).where(DevicePort.id == port.id))
    assert res.scalar_one_or_none() is None

    # PduOutlet should be gone
    res = await db.execute(select(PduOutlet).where(PduOutlet.id == outlet.id))
    assert res.scalar_one_or_none() is None

    # Cable should still exist, but von_device_id should be NULL (SET NULL)
    res = await db.execute(
        select(Cable)
        .where(Cable.id == cable.id)
        .execution_options(populate_existing=True)
    )
    db_cable = res.scalar_one_or_none()
    assert db_cable is not None
    assert db_cable.von_device_id is None

    # CableStrand should still exist, but von_port_id should be NULL (SET NULL)
    res = await db.execute(
        select(CableStrand)
        .where(CableStrand.id == strand.id)
        .execution_options(populate_existing=True)
    )
    db_strand = res.scalar_one_or_none()
    assert db_strand is not None
    assert db_strand.von_port_id is None

