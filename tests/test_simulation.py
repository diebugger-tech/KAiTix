import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Rack, Device, PduOutlet
from app.domains.hardware.models import DeviceDependency
from app.domains.simulation.services import validate_no_cycles


@pytest.mark.asyncio
async def test_validate_no_cycles_linear_ok(db: AsyncSession):
    # Setup test devices
    rack = Rack(name="Test Rack", standort="Room 1")
    db.add(rack)
    await db.flush()

    d1 = Device(hostname="dev-1", typ="server", rack_id=rack.id)
    d2 = Device(hostname="dev-2", typ="server", rack_id=rack.id)
    db.add_all([d1, d2])
    await db.flush()

    # Linear: d1 depends on d2. No cycle.
    ok = await validate_no_cycles(db, d1.id, [d2.id])
    assert ok is True


@pytest.mark.asyncio
async def test_validate_no_cycles_self_cycle(db: AsyncSession):
    rack = Rack(name="Test Rack", standort="Room 1")
    db.add(rack)
    await db.flush()

    d1 = Device(hostname="dev-1", typ="server", rack_id=rack.id)
    db.add(d1)
    await db.flush()

    # Self dependency: d1 depends on d1. Cycle detected.
    ok = await validate_no_cycles(db, d1.id, [d1.id])
    assert ok is False


@pytest.mark.asyncio
async def test_validate_no_cycles_simple_cycle(db: AsyncSession):
    rack = Rack(name="Test Rack", standort="Room 1")
    db.add(rack)
    await db.flush()

    d1 = Device(hostname="dev-1", typ="server", rack_id=rack.id)
    d2 = Device(hostname="dev-2", typ="server", rack_id=rack.id)
    db.add_all([d1, d2])
    await db.flush()

    # Add existing dependency: d2 depends on d1
    dep1 = DeviceDependency(device_id=d2.id, depends_on_device_id=d1.id)
    db.add(dep1)
    await db.commit()

    # Try to add: d1 depends on d2. Cycle detected (d1 -> d2 -> d1).
    ok = await validate_no_cycles(db, d1.id, [d2.id])
    assert ok is False


@pytest.mark.asyncio
async def test_validate_no_cycles_complex_cycle(db: AsyncSession):
    rack = Rack(name="Test Rack", standort="Room 1")
    db.add(rack)
    await db.flush()

    d1 = Device(hostname="dev-1", typ="server", rack_id=rack.id)
    d2 = Device(hostname="dev-2", typ="server", rack_id=rack.id)
    d3 = Device(hostname="dev-3", typ="server", rack_id=rack.id)
    db.add_all([d1, d2, d3])
    await db.flush()

    # Existing: d3 depends on d2, d2 depends on d1
    dep1 = DeviceDependency(device_id=d3.id, depends_on_device_id=d2.id)
    dep2 = DeviceDependency(device_id=d2.id, depends_on_device_id=d1.id)
    db.add_all([dep1, dep2])
    await db.commit()

    # Try to add: d1 depends on d3. Cycle detected (d1 -> d3 -> d2 -> d1).
    ok = await validate_no_cycles(db, d1.id, [d3.id])
    assert ok is False


@pytest.mark.asyncio
async def test_simulation_power_loss_and_cascading(
    client: AsyncClient, db: AsyncSession
):
    rack = Rack(name="Simulation Rack", standort="Room 1")
    db.add(rack)
    await db.flush()

    # PDU
    pdu = Device(hostname="rack-pdu-1", typ="pdu", rack_id=rack.id)
    db.add(pdu)
    await db.flush()

    # Outlets
    o1 = PduOutlet(pdu_id=pdu.id, outlet_name="Outlet L1", phase="L1")
    o2 = PduOutlet(pdu_id=pdu.id, outlet_name="Outlet L2", phase="L2")
    db.add_all([o1, o2])
    await db.flush()

    # Devices
    # Server 1 has single power supply on L1
    s1 = Device(
        hostname="server-single-psu",
        typ="server",
        rack_id=rack.id,
        shutdown_priority=1,
        shutdown_delay_seconds=30,
        shutdown_method="ACPI_Graceful",
    )
    # Server 2 has dual redundant power supplies (L1 and L2)
    s2 = Device(
        hostname="server-dual-psu",
        typ="server",
        rack_id=rack.id,
        shutdown_priority=2,
        shutdown_delay_seconds=60,
        shutdown_method="SSH_Script",
    )
    # Server 3 depends on server-single-psu
    s3 = Device(
        hostname="server-dependent",
        typ="server",
        rack_id=rack.id,
        shutdown_priority=3,
        shutdown_delay_seconds=45,
        shutdown_method="Hard_Power_Cut_PDU",
    )
    db.add_all([s1, s2, s3])
    await db.flush()

    # Connect them to outlets
    o1.connected_device_id = s1.id
    # s2 connects to both L1 (o1 equivalent, let's create connected outlets)
    # Let's define the connection by updating connected_device_id
    await db.flush()

    o1_s2 = PduOutlet(
        pdu_id=pdu.id, outlet_name="Outlet L1-s2", phase="L1", connected_device_id=s2.id
    )
    o2_s2 = PduOutlet(
        pdu_id=pdu.id, outlet_name="Outlet L2-s2", phase="L2", connected_device_id=s2.id
    )
    db.add_all([o1_s2, o2_s2])
    await db.flush()

    # Also s1 is connected to o1
    o1.connected_device_id = s1.id

    # Add dependency: s3 depends on s1
    dep = DeviceDependency(
        device_id=s3.id, depends_on_device_id=s1.id, dependency_type="service"
    )
    db.add(dep)
    await db.commit()

    # Scenario: Loss of Phase L1
    payload = {"target_type": "phase", "target_name": "L1"}

    response = await client.post("/api/v1/simulation/run", json=payload)
    if response.status_code != 200:
        print("ERROR BODY:", response.json())
    assert response.status_code == 200
    data = response.json()

    # Verify states:
    # s1: red (only L1 power)
    # s2: yellow (lost L1, still has L2)
    # s3: red (depends on s1 which is red)
    affected = {item["device_id"]: item for item in data["affected_devices"]}

    assert affected[s1.id]["state"] == "red"
    assert affected[s2.id]["state"] == "yellow"
    assert affected[s3.id]["state"] == "red"

    # Verify timeline event order: shutdown order (priority 1 -> priority 3)
    # Filter only events for s1 and s3
    events = data["shutdown_timeline"]
    assert len(events) >= 2

    # Sort events by time_seconds or sequence order
    assert events[0]["device_id"] == s1.id
    assert events[0]["action"] == "shutdown"
    assert events[0]["method"] == "ACPI_Graceful"

    assert events[1]["device_id"] == s3.id
    assert events[1]["action"] == "shutdown"
    assert events[1]["method"] == "Hard_Power_Cut_PDU"

    # Boot timeline: reverse order
    boot_events = data["boot_timeline"]
    assert len(boot_events) >= 2
    assert boot_events[0]["device_id"] == s3.id
    assert boot_events[0]["action"] == "boot"
    assert boot_events[1]["device_id"] == s1.id
    assert boot_events[1]["action"] == "boot"


@pytest.mark.asyncio
async def test_simulation_ha_grouping(client: AsyncClient, db: AsyncSession):
    rack = Rack(name="HA Rack", standort="Room 1")
    db.add(rack)
    await db.flush()

    pdu = Device(hostname="rack-pdu-ha", typ="pdu", rack_id=rack.id)
    db.add(pdu)
    await db.flush()

    # Outlets
    o1 = PduOutlet(pdu_id=pdu.id, outlet_name="Outlet L1", phase="L1")
    db.add(o1)
    await db.flush()

    # DB Cluster Node A & Node B (HA cluster)
    db_a = Device(hostname="db-node-a", typ="server", rack_id=rack.id)
    db_b = Device(hostname="db-node-b", typ="server", rack_id=rack.id)
    # App server
    app_srv = Device(hostname="app-srv", typ="server", rack_id=rack.id)
    db.add_all([db_a, db_b, app_srv])
    await db.flush()

    # db_a is on L1 outlet (it will fail when L1 fails)
    o1.connected_device_id = db_a.id

    # db_b is NOT on L1 outlet, it stays green
    # app_srv depends on (db_a OR db_b) as "db_cluster" group
    dep1 = DeviceDependency(
        device_id=app_srv.id,
        depends_on_device_id=db_a.id,
        dependency_group="db_cluster",
    )
    dep2 = DeviceDependency(
        device_id=app_srv.id,
        depends_on_device_id=db_b.id,
        dependency_group="db_cluster",
    )
    db.add_all([dep1, dep2])
    await db.commit()

    # Scenario: Loss of Phase L1 (db_a fails, but db_b is ok)
    payload = {"target_type": "phase", "target_name": "L1"}

    response = await client.post("/api/v1/simulation/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    affected_ids = [item["device_id"] for item in data["affected_devices"]]

    # db_a must be red (failed)
    assert db_a.id in affected_ids
    affected_db_a = next(
        item for item in data["affected_devices"] if item["device_id"] == db_a.id
    )
    assert affected_db_a["state"] == "red"

    # app_srv must NOT be affected (green) because db_b is still active
    assert app_srv.id not in affected_ids


@pytest.mark.asyncio
async def test_simulation_pdu_path_failure(client: AsyncClient, db: AsyncSession):
    rack = Rack(name="Redundancy Rack", standort="Room 1")
    db.add(rack)
    await db.flush()

    # Create PDUs
    pdu_a = Device(
        hostname="pdu-a",
        typ="pdu",
        rack_id=rack.id,
        redundancy_path="A",
        absicherung_a=16.0,
        strom_typ="3-phasig",
        spannung_v=400,
    )
    pdu_b = Device(
        hostname="pdu-b",
        typ="pdu",
        rack_id=rack.id,
        redundancy_path="B",
        absicherung_a=16.0,
        strom_typ="3-phasig",
        spannung_v=400,
    )
    db.add_all([pdu_a, pdu_b])
    await db.flush()

    # Create Outlets
    o_a = PduOutlet(pdu_id=pdu_a.id, outlet_name="Outlet-A", redundancy_path="A")
    o_b = PduOutlet(pdu_id=pdu_b.id, outlet_name="Outlet-B", redundancy_path="B")
    db.add_all([o_a, o_b])
    await db.flush()

    # Create Servers
    srv_single = Device(
        hostname="srv-single", typ="server", rack_id=rack.id, psu_count=1
    )
    srv_dual = Device(hostname="srv-dual", typ="server", rack_id=rack.id, psu_count=2)
    db.add_all([srv_single, srv_dual])
    await db.flush()

    # Connect Servers to Outlets
    o_a.connected_device_id = srv_single.id

    # Dual server connects to both
    o_a_dual = PduOutlet(
        pdu_id=pdu_a.id,
        outlet_name="Outlet-A2",
        redundancy_path="A",
        connected_device_id=srv_dual.id,
    )
    o_b_dual = PduOutlet(
        pdu_id=pdu_b.id,
        outlet_name="Outlet-B2",
        redundancy_path="B",
        connected_device_id=srv_dual.id,
    )
    db.add_all([o_a_dual, o_b_dual])

    await db.commit()

    # Simulate path A failure
    payload = {"target_type": "pdu_path", "target_name": "A"}

    response = await client.post("/api/v1/simulation/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verify device states:
    # pdu-a: red
    # srv-single: red
    # srv-dual: yellow
    affected = {item["device_id"]: item for item in data["affected_devices"]}

    assert affected[pdu_a.id]["state"] == "red"
    assert affected[srv_single.id]["state"] == "red"
    assert affected[srv_dual.id]["state"] == "yellow"
    assert pdu_b.id not in affected


@pytest.mark.asyncio
async def test_scorer_pdu_anomalies(db: AsyncSession):
    from app.domains.simulation.services import AnomalyScorer

    rack = Rack(name="Scorer Rack", standort="Room 2", hoehe_u=42)
    db.add(rack)
    await db.flush()

    # 1. PDU with incompatible height (min_rack_hoehe=47 in a 42 HE rack)
    pdu_inc = Device(
        hostname="pdu-incompatible",
        typ="pdu",
        rack_id=rack.id,
        min_rack_hoehe=47,
        redundancy_path="A",
        absicherung_a=16.0,
        strom_typ="3-phasig",
        spannung_v=400,
    )
    db.add(pdu_inc)
    await db.commit()

    # Check anomaly scores
    res = AnomalyScorer.score_all_racks([rack], [pdu_inc], [], set())
    assert len(res) == 1
    # Should flag height incompatibility
    issues = res[0]["issues"]
    assert any("inkompatibel" in i for i in issues)
    # Check score contributes to total
    assert res[0]["score"] > 0.0
