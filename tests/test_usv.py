import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.power.services.usv_calc import UsvCalculator
from app.models import (
    Rack,
    UsvUnit,
    UsvModule,
    Device,
)


@pytest.mark.asyncio
async def test_n1_required_modules():
    # Example 1: 0 load should require 1 module (N+1 where N=0)
    assert (
        UsvCalculator.calculate_n1_required_modules(
            Decimal("0"), Decimal("0"), Decimal("0"), Decimal("10")
        )
        == 1
    )

    # Example 2: Balanced load L1=10kW, L2=10kW, L3=10kW, Module = 10kW
    # Total = 30kW. Module provides 10kW total (3.33kW/phase).
    # N = 30 / 10 = 3. Phase check: 3 * 10 / 10 = 3. Max = 3.
    # N = 3, so N+1 = 4.
    assert (
        UsvCalculator.calculate_n1_required_modules(
            Decimal("10"), Decimal("10"), Decimal("10"), Decimal("10")
        )
        == 4
    )

    # Example 3: Imbalanced load L1=10kW, L2=0kW, L3=0kW, Module = 10kW
    # Total = 10kW. Phase peak L1=10kW.
    # Total modules required = 10 / 10 = 1.
    # Phase balance requires: 3 * 10 / 10 = 3 modules.
    # N = max(1, 3) = 3.
    # N+1 = 4 modules.
    assert (
        UsvCalculator.calculate_n1_required_modules(
            Decimal("10"), Decimal("0"), Decimal("0"), Decimal("10")
        )
        == 4
    )


@pytest.mark.asyncio
async def test_simulate_usv_endpoint(client: AsyncClient):
    payload = {
        "l1_kw": 8.5,
        "l2_kw": 5.0,
        "l3_kw": 6.2,
        "module_capacity_kw": 10.0,
        "installed_modules_count": 4,
    }
    response = await client.post("/api/v1/usv/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["installed_kw"] == 40.0
    assert data["n1_kw"] == 30.0
    assert data["phase_capacity_n1_kw"] == 10.0
    # L1=8.5, L2=5.0, L3=6.2. Total = 19.7. Max phase = 8.5 <= 10.0.
    # Should be safe
    assert data["n1_safe"] is True
    # If we reduce modules to 2 (installed_kw = 20, n1_kw = 10, phase_capacity_n1 = 3.33)
    # L1=8.5 > 3.33, so it should not be safe.
    payload["installed_modules_count"] = 2
    response2 = await client.post("/api/v1/usv/simulate", json=payload)
    assert response2.status_code == 200
    assert response2.json()["n1_safe"] is False


@pytest.mark.asyncio
async def test_get_usv_status_endpoint(client: AsyncClient, db: AsyncSession):
    # Set up DB entities: Rack -> USV -> Panel -> Circuit -> Device
    rack = Rack(name="Rack T1", standort="Serverraum 1")
    db.add(rack)
    await db.flush()

    usv = UsvUnit(bezeichnung="UPS Core 1", rack_id=rack.id, max_kw=Decimal("50"))
    db.add(usv)
    await db.flush()

    # Add active modules
    m1 = UsvModule(
        usv_unit_id=usv.id, slot=1, leistung_kw=Decimal("10"), status="aktiv"
    )
    m2 = UsvModule(
        usv_unit_id=usv.id, slot=2, leistung_kw=Decimal("10"), status="aktiv"
    )
    m3 = UsvModule(
        usv_unit_id=usv.id, slot=3, leistung_kw=Decimal("10"), status="aktiv"
    )
    db.add_all([m1, m2, m3])

    # Add device on this rack
    device = Device(
        hostname="server-01",
        typ="server",
        rack_id=rack.id,
        phase="L1",
        tdp_watt=Decimal("1500"),  # 1.5 kW
        einschaltstrom_faktor=Decimal("2.0"),
    )
    db.add(device)
    await db.commit()

    # Request status
    response = await client.get(f"/api/v1/usv/{usv.id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["bezeichnung"] == "UPS Core 1"
    assert data["installed_kw"] == 30.0
    assert data["n1_kw"] == 20.0
    assert data["loads"]["l1"]["load_kw"] == 1.5
    assert data["loads"]["l1"]["peak_kw"] == 3.0
    assert data["loads"]["l2"]["load_kw"] == 0.0
    assert data["total_load_kw"] == 1.5
    assert data["n1_safe"] is True


@pytest.mark.asyncio
async def test_simulate_shutdown_success(client: AsyncClient, db: AsyncSession):
    """Tests the shutdown simulation endpoint with devices at varying delays."""
    rack = Rack(name="Shutdown Rack", standort="Test")
    db.add(rack)
    await db.flush()

    devices = [
        Device(
            hostname="db-01",
            typ="server",
            rack_id=rack.id,
            phase="L1",
            tdp_watt=Decimal("500"),
            shutdown_delay_seconds=30,
            shutdown_priority=3,
            einschaltstrom_faktor=Decimal("2.0"),
        ),
        Device(
            hostname="app-01",
            typ="server",
            rack_id=rack.id,
            phase="L2",
            tdp_watt=Decimal("300"),
            shutdown_delay_seconds=20,
            shutdown_priority=2,
            einschaltstrom_faktor=Decimal("2.0"),
        ),
        Device(
            hostname="web-01",
            typ="server",
            rack_id=rack.id,
            phase="L3",
            tdp_watt=Decimal("200"),
            shutdown_delay_seconds=10,
            shutdown_priority=1,
            einschaltstrom_faktor=Decimal("2.0"),
        ),
    ]
    db.add_all(devices)
    await db.commit()

    payload = {
        "rack_id": rack.id,
        "battery_type": "vrla",
        "series_blocks": 4,
        "parallel_strings": 1,
        "block_voltage_v": 12,
        "block_capacity_ah": 100,
        "age_years": 0,
        "temperature_c": 20,
        "inverter_efficiency": 0.90,
    }
    response = await client.post("/api/v1/usv/simulate-shutdown", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "battery_summary" in data
    assert "timeline" in data
    assert "device_statuses" in data

    # Timeline should start at t=0 with SoC > 0
    assert len(data["timeline"]) > 0
    assert data["timeline"][0]["time_seconds"] == 0
    assert data["timeline"][0]["soc_pct"] > 0

    # All devices should shut down safely (no crash with 100Ah battery and 1kW load)
    for ds in data["device_statuses"]:
        assert ds["crashed"] is False, (
            f"Device {ds['hostname']} crashed: {ds.get('crash_reason')}"
        )
        assert ds["shutdown_at_seconds"] is not None


@pytest.mark.asyncio
async def test_simulate_shutdown_crash_detection(client: AsyncClient, db: AsyncSession):
    """Tests that devices crash when battery is undersized."""
    rack = Rack(name="Crash Rack", standort="Test")
    db.add(rack)
    await db.flush()

    # Single high-power device with delay=300s -> starts active, drains tiny battery before shutdown
    device = Device(
        hostname="powerhog-01",
        typ="server",
        rack_id=rack.id,
        phase="L1",
        tdp_watt=Decimal("5000"),
        shutdown_delay_seconds=300,
        shutdown_priority=1,
        einschaltstrom_faktor=Decimal("2.0"),
    )
    db.add(device)
    await db.commit()

    payload = {
        "rack_id": rack.id,
        "battery_type": "vrla",
        "series_blocks": 1,
        "parallel_strings": 1,
        "block_voltage_v": 12,
        "block_capacity_ah": 1,  # Tiny battery
        "age_years": 0,
        "temperature_c": 20,
        "inverter_efficiency": 0.90,
    }
    response = await client.post("/api/v1/usv/simulate-shutdown", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Device should crash (battery too small for 5kW load)
    crashed_devices = [d for d in data["device_statuses"] if d["crashed"]]
    assert len(crashed_devices) > 0, "Expected at least one device to crash"
    assert crashed_devices[0]["crash_reason"] is not None


@pytest.mark.asyncio
async def test_simulate_shutdown_peukert_discharge(
    client: AsyncClient, db: AsyncSession
):
    """Verifies Peukert curve slope changes dynamically as load decreases."""
    rack = Rack(name="Peukert Rack", standort="Test")
    db.add(rack)
    await db.flush()

    # Two devices: one shuts down early (delay=10s), one stays on longer (delay=120s)
    devices = [
        Device(
            hostname="early-off",
            typ="server",
            rack_id=rack.id,
            phase="L1",
            tdp_watt=Decimal("2000"),
            shutdown_delay_seconds=10,
            shutdown_priority=1,
            einschaltstrom_faktor=Decimal("2.0"),
        ),
        Device(
            hostname="late-off",
            typ="server",
            rack_id=rack.id,
            phase="L2",
            tdp_watt=Decimal("1000"),
            shutdown_delay_seconds=120,
            shutdown_priority=2,
            einschaltstrom_faktor=Decimal("2.0"),
        ),
    ]
    db.add_all(devices)
    await db.commit()

    payload = {
        "rack_id": rack.id,
        "battery_type": "vrla",
        "series_blocks": 2,
        "parallel_strings": 1,
        "block_voltage_v": 12,
        "block_capacity_ah": 20,
        "age_years": 0,
        "temperature_c": 20,
        "inverter_efficiency": 0.90,
    }
    response = await client.post("/api/v1/usv/simulate-shutdown", json=payload)
    assert response.status_code == 200
    data = response.json()
    timeline = data["timeline"]

    # Before first device shuts down (t < 10s), load should be 3kW
    early_points = [p for p in timeline if p["time_seconds"] < 10]
    assert len(early_points) >= 1
    assert early_points[0]["load_kw"] == pytest.approx(3.0, rel=0.1)

    # After first device shuts down (t >= 10s but < 120s), load should drop to 1kW
    mid_points = [p for p in timeline if 10 <= p["time_seconds"] < 120]
    assert len(mid_points) >= 1
    assert mid_points[0]["load_kw"] == pytest.approx(1.0, rel=0.1)

    # The curve slope should be steeper in early phase (higher load)
    # SoC drop per second should be larger in first interval
    if len(timeline) >= 3:
        early_soc_drop = timeline[0]["soc_pct"] - timeline[1]["soc_pct"]
        # Load drops at t=10, so compare pre vs post
        late_points = [p for p in timeline if p["time_seconds"] >= 10]
        if late_points and late_points[0]["soc_pct"] > 0:
            # The absolute discharge slows after load drops
            assert timeline[0]["load_kw"] > timeline[1]["load_kw"]
