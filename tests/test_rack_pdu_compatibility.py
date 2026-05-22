import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Rack, Device


@pytest.mark.asyncio
async def test_device_creation_min_rack_hoehe_validation(
    client: AsyncClient, db: AsyncSession
):
    # 1. Create a rack with insufficient height (40 HE)
    rack_small = Rack(name="Small Rack 40HE", standort="Room A", hoehe_u=40)
    db.add(rack_small)
    await db.commit()

    # 2. Attempt to add a 42HE vertical PDU to the 40HE rack (ID 16 from catalog: Kentix SmartPDU 3P-16A)
    device_payload = {
        "hostname": "pdu-small-rack",
        "typ": "pdu",
        "u_position": None,
        "u_hoehe": 0,
        "hersteller": "Kentix",
        "modell": "SmartPDU Vertikal 40HE 3P-16A",
        "rack_id": rack_small.id,
    }

    response = await client.post("/api/v1/devices/", json=device_payload)
    assert response.status_code == 400
    assert "Kompatibilitätsfehler" in response.text
    assert "benötigt ein Rack mit mindestens 42 HE" in response.text

    # 3. Create a rack with sufficient height (42 HE)
    rack_large = Rack(name="Normal Rack 42HE", standort="Room A", hoehe_u=42)
    db.add(rack_large)
    await db.commit()

    # 4. Add the same PDU to the 42HE rack - should succeed
    device_payload["rack_id"] = rack_large.id
    response_ok = await client.post("/api/v1/devices/", json=device_payload)
    assert response_ok.status_code == 201


@pytest.mark.asyncio
async def test_rack_shrink_validation(client: AsyncClient, db: AsyncSession):
    # 1. Create a rack with 42 HE
    rack = Rack(name="Shrink Test Rack", standort="Room B", hoehe_u=42)
    db.add(rack)
    await db.commit()

    # 2. Add a Kentix SmartPDU 3P-16A (needs 42 HE)
    pdu = Device(
        hostname="pdu-shrink-test",
        typ="pdu",
        u_position=None,
        u_hoehe=0,
        hersteller="Kentix",
        modell="SmartPDU Vertikal 40HE 3P-16A",
        rack_id=rack.id,
    )
    db.add(pdu)
    await db.commit()

    # 3. Try to shrink the rack to 40 HE - should fail
    shrink_payload = {"name": "Shrink Test Rack", "standort": "Room B", "hoehe_u": 40}
    response = await client.put(f"/api/v1/racks/{rack.id}", json=shrink_payload)
    assert response.status_code == 400
    assert "Höhenkonflikt" in response.text
    assert "mindestens 42 HE benötigt" in response.text

    # 4. Try updating rack parameters without shrinking below 42 HE - should succeed
    ok_payload = {
        "name": "Updated Shrink Test Rack",
        "standort": "Room B",
        "hoehe_u": 45,
    }
    response_ok = await client.put(f"/api/v1/racks/{rack.id}", json=ok_payload)
    assert response_ok.status_code == 200
    data = response_ok.json()
    assert data["hoehe_u"] == 45
    assert data["name"] == "Updated Shrink Test Rack"


@pytest.mark.asyncio
async def test_rack_template_fields_persistence(client: AsyncClient, db: AsyncSession):
    # 1. Create a rack with template metadata
    rack_payload = {
        "name": "Template Rack 1",
        "standort": "Room C",
        "hoehe_u": 42,
        "hersteller": "Rittal",
        "modell": "VX IT 42HE",
        "hardware_type_id": 25,
    }
    response = await client.post("/api/v1/racks/", json=rack_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["hersteller"] == "Rittal"
    assert data["modell"] == "VX IT 42HE"
    assert data["hardware_type_id"] == 25

    # 2. Update the rack template metadata
    update_payload = {
        "hersteller": "Rittal Updated",
        "modell": "VX IT 47HE",
        "hardware_type_id": 26,
        "hoehe_u": 47,
    }
    response_update = await client.put(
        f"/api/v1/racks/{data['id']}", json=update_payload
    )
    assert response_update.status_code == 200
    data_update = response_update.json()
    assert data_update["hersteller"] == "Rittal Updated"
    assert data_update["modell"] == "VX IT 47HE"
    assert data_update["hardware_type_id"] == 26
    assert data_update["hoehe_u"] == 47
