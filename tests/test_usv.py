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
