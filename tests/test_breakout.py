from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CableStrand, Device, Kabeltyp, Rack


async def _devices(db: AsyncSession, count: int = 6) -> list[Device]:
    rack = Rack(name="Breakout-Test-Rack", standort="Test")
    db.add(rack)
    await db.flush()
    devices = [
        Device(hostname=f"breakout-test-{index}", typ="server", rack_id=rack.id)
        for index in range(count)
    ]
    db.add_all(devices)
    await db.flush()
    return devices


async def _typ(
    db: AsyncSession, name: str, *, enden_b: int = 1, kategorie: str = "kupfer"
) -> Kabeltyp:
    kabeltyp = Kabeltyp(
        name=name,
        kategorie=kategorie,
        stecker_a="A",
        stecker_b="B",
        enden_a=1,
        enden_b=enden_b,
        alt_typ="sonstige" if enden_b > 1 else name,
        aktiv=True,
    )
    db.add(kabeltyp)
    await db.flush()
    return kabeltyp


async def _breakout(db: AsyncSession) -> Kabeltyp:
    return await _typ(db, "Breakout QSFP+→4×SFP+", enden_b=4, kategorie="breakout")


def _straenge(devices: list[Device], count: int = 4) -> list[dict]:
    return [
        {
            "strand_number": nummer,
            "nach_device_id": devices[nummer].id,
            "nach_port": f"sfp{nummer}",
        }
        for nummer in range(1, count + 1)
    ]


async def _post(client: AsyncClient, **felder):
    return await client.post("/api/v1/cables/", json={"laenge_m": 1, **felder})


async def test_breakout_mit_vier_straengen_anlegen_lesen_aendern(
    client: AsyncClient, db: AsyncSession
):
    devices = await _devices(db)
    breakout = await _breakout(db)

    created = await _post(
        client,
        kabeltyp_id=breakout.id,
        von_device_id=devices[0].id,
        von_port="qsfp1",
        straenge=_straenge(devices),
    )
    assert created.status_code == 201, created.text
    cable = created.json()
    assert cable["nach_device_id"] is None
    assert cable["nach_port"] is None
    assert [s["strand_number"] for s in cable["cable_strands"]] == [1, 2, 3, 4]
    assert [s["nach_device_id"] for s in cable["cable_strands"]] == [
        devices[1].id,
        devices[2].id,
        devices[3].id,
        devices[4].id,
    ]
    assert [s["nach_port"] for s in cable["cable_strands"]] == [
        "sfp1",
        "sfp2",
        "sfp3",
        "sfp4",
    ]

    read = await client.get(f"/api/v1/cables/{cable['id']}")
    assert read.status_code == 200, read.text
    assert read.json()["cable_strands"] == cable["cable_strands"]

    geaendert = _straenge(devices)
    geaendert[3] = {
        "strand_number": 4,
        "nach_device_id": devices[5].id,
        "nach_port": "sfp9",
        "farbe": "Gelb",
    }
    updated = await client.put(
        f"/api/v1/cables/{cable['id']}", json={"straenge": geaendert}
    )
    assert updated.status_code == 200, updated.text
    straenge = updated.json()["cable_strands"]
    assert len(straenge) == 4
    assert straenge[3]["nach_device_id"] == devices[5].id
    assert straenge[3]["nach_port"] == "sfp9"
    assert straenge[3]["farbe"] == "Gelb"

    in_db = await db.execute(
        select(CableStrand).where(CableStrand.cable_id == cable["id"])
    )
    assert len(in_db.scalars().all()) == 4


async def test_drei_straenge_bei_enden_b_vier_ergibt_422(
    client: AsyncClient, db: AsyncSession
):
    devices = await _devices(db)
    breakout = await _breakout(db)

    response = await _post(
        client,
        kabeltyp_id=breakout.id,
        von_device_id=devices[0].id,
        von_port="qsfp1",
        straenge=_straenge(devices, count=3),
    )

    assert response.status_code == 422, response.text
    assert "4" in response.json()["detail"]


async def test_breakout_ohne_straenge_ergibt_422(client: AsyncClient, db: AsyncSession):
    breakout = await _breakout(db)

    response = await _post(client, kabeltyp_id=breakout.id)

    assert response.status_code == 422, response.text


async def test_doppelte_strangnummer_ergibt_422(client: AsyncClient, db: AsyncSession):
    devices = await _devices(db)
    breakout = await _breakout(db)
    straenge = _straenge(devices)
    straenge[3]["strand_number"] = 1

    response = await _post(client, kabeltyp_id=breakout.id, straenge=straenge)

    assert response.status_code == 422, response.text


async def test_straenge_an_normalem_kabel_ergeben_422(
    client: AsyncClient, db: AsyncSession
):
    devices = await _devices(db)
    cat = await _typ(db, "Cat6A")

    response = await _post(
        client, kabeltyp_id=cat.id, straenge=_straenge(devices, count=1)
    )

    assert response.status_code == 422, response.text


async def test_breakout_mit_ziel_am_kabel_ergibt_422(
    client: AsyncClient, db: AsyncSession
):
    devices = await _devices(db)
    breakout = await _breakout(db)

    response = await _post(
        client,
        kabeltyp_id=breakout.id,
        nach_device_id=devices[5].id,
        nach_port="eth0",
        straenge=_straenge(devices),
    )

    assert response.status_code == 422, response.text


async def test_strang_auf_belegtem_port_ergibt_409(
    client: AsyncClient, db: AsyncSession
):
    devices = await _devices(db)
    cat = await _typ(db, "Cat6A")
    breakout = await _breakout(db)
    belegt = await _post(
        client,
        kabel_nr="KAB-0001",
        kabeltyp_id=cat.id,
        von_device_id=devices[0].id,
        von_port="eth0",
        nach_device_id=devices[2].id,
        nach_port="sfp2",
    )
    assert belegt.status_code == 201, belegt.text

    response = await _post(
        client,
        kabeltyp_id=breakout.id,
        von_device_id=devices[5].id,
        von_port="qsfp1",
        straenge=_straenge(devices),
    )

    assert response.status_code == 409, response.text
    assert "KAB-0001" in response.json()["detail"]
    assert "sfp2" in response.json()["detail"]


async def test_normales_kabel_auf_strang_port_ergibt_409(
    client: AsyncClient, db: AsyncSession
):
    devices = await _devices(db)
    cat = await _typ(db, "Cat6A")
    breakout = await _breakout(db)
    created = await _post(
        client,
        kabel_nr="KAB-0100",
        kabeltyp_id=breakout.id,
        von_device_id=devices[0].id,
        von_port="qsfp1",
        straenge=_straenge(devices),
    )
    assert created.status_code == 201, created.text

    response = await _post(
        client,
        kabeltyp_id=cat.id,
        von_device_id=devices[5].id,
        von_port="eth0",
        nach_device_id=devices[3].id,
        nach_port="sfp3",
    )

    assert response.status_code == 409, response.text
    assert "KAB-0100" in response.json()["detail"]


async def test_zwei_straenge_auf_demselben_port_ergeben_409(
    client: AsyncClient, db: AsyncSession
):
    devices = await _devices(db)
    breakout = await _breakout(db)
    straenge = _straenge(devices)
    straenge[1]["nach_device_id"] = devices[1].id
    straenge[1]["nach_port"] = "sfp1"

    response = await _post(client, kabeltyp_id=breakout.id, straenge=straenge)

    assert response.status_code == 409, response.text


async def test_typwechsel_breakout_zu_cat6a_entfernt_straenge(
    client: AsyncClient, db: AsyncSession
):
    devices = await _devices(db)
    cat = await _typ(db, "Cat6A")
    breakout = await _breakout(db)
    created = (
        await _post(
            client,
            kabeltyp_id=breakout.id,
            von_device_id=devices[0].id,
            von_port="qsfp1",
            straenge=_straenge(devices),
        )
    ).json()

    response = await client.put(
        f"/api/v1/cables/{created['id']}",
        json={
            "kabeltyp_id": cat.id,
            "nach_device_id": devices[1].id,
            "nach_port": "eth0",
        },
    )

    assert response.status_code == 200, response.text
    cable = response.json()
    assert cable["typ"] == "Cat6A"
    assert cable["cable_strands"] == []
    assert cable["nach_device_id"] == devices[1].id
    in_db = await db.execute(
        select(CableStrand).where(CableStrand.cable_id == created["id"])
    )
    assert in_db.scalars().all() == []


async def test_typwechsel_cat6a_zu_breakout_leert_ziel_am_kabel(
    client: AsyncClient, db: AsyncSession
):
    devices = await _devices(db)
    cat = await _typ(db, "Cat6A")
    breakout = await _breakout(db)
    created = (
        await _post(
            client,
            kabeltyp_id=cat.id,
            von_device_id=devices[0].id,
            von_port="qsfp1",
            nach_device_id=devices[5].id,
            nach_port="eth0",
        )
    ).json()

    ohne_straenge = await client.put(
        f"/api/v1/cables/{created['id']}", json={"kabeltyp_id": breakout.id}
    )
    assert ohne_straenge.status_code == 422, ohne_straenge.text

    response = await client.put(
        f"/api/v1/cables/{created['id']}",
        json={"kabeltyp_id": breakout.id, "straenge": _straenge(devices)},
    )

    assert response.status_code == 200, response.text
    cable = response.json()
    assert cable["nach_device_id"] is None
    assert cable["nach_port"] is None
    assert len(cable["cable_strands"]) == 4


async def test_breakout_andere_felder_aendern_behaelt_straenge(
    client: AsyncClient, db: AsyncSession
):
    devices = await _devices(db)
    breakout = await _breakout(db)
    created = (
        await _post(
            client,
            kabeltyp_id=breakout.id,
            von_device_id=devices[0].id,
            von_port="qsfp1",
            straenge=_straenge(devices),
        )
    ).json()

    response = await client.put(
        f"/api/v1/cables/{created['id']}", json={"bemerkung": "geprüft"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["bemerkung"] == "geprüft"
    assert response.json()["cable_strands"] == created["cable_strands"]


async def test_enden_eines_verwendeten_typs_aendern_ergibt_409(
    client: AsyncClient, db: AsyncSession
):
    devices = await _devices(db)
    breakout = await _breakout(db)
    await _post(client, kabeltyp_id=breakout.id, straenge=_straenge(devices))

    response = await client.put(
        f"/api/v1/kabeltypen/{breakout.id}", json={"enden_b": 8}
    )

    assert response.status_code == 409, response.text
    assert "1 Kabel" in response.json()["detail"]
