from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Kabeltyp


async def _seed_typ(
    db: AsyncSession,
    name: str,
    *,
    kategorie: str = "kupfer",
    stecker_a: str = "RJ45",
    stecker_b: str = "RJ45",
    enden_b: int = 1,
    standard_farbe: str | None = None,
    alt_typ: str | None = None,
    aktiv: bool = True,
) -> Kabeltyp:
    kabeltyp = Kabeltyp(
        name=name,
        kategorie=kategorie,
        stecker_a=stecker_a,
        stecker_b=stecker_b,
        enden_a=1,
        enden_b=enden_b,
        standard_farbe=standard_farbe,
        alt_typ=alt_typ if alt_typ is not None else name,
        aktiv=aktiv,
    )
    db.add(kabeltyp)
    await db.flush()
    return kabeltyp


async def _seed_breakout(db: AsyncSession) -> Kabeltyp:
    return await _seed_typ(
        db,
        "Breakout QSFP+→4×SFP+",
        kategorie="breakout",
        stecker_a="QSFP+",
        stecker_b="SFP+",
        enden_b=4,
        alt_typ="sonstige",
    )


async def _post_cable(client: AsyncClient, **felder):
    payload = {"laenge_m": 1, **felder}
    return await client.post("/api/v1/cables/", json=payload)


# === Kabel-Schreibweg mit Katalog ============================================
async def test_kabel_mit_kabeltyp_id_setzt_typ_und_standardfarbe(
    client: AsyncClient, db: AsyncSession
):
    lc = await _seed_typ(
        db,
        "LC-LC",
        kategorie="lwl",
        stecker_a="LC-Duplex",
        stecker_b="LC-Duplex",
        standard_farbe="Erika-Violett",
    )

    response = await _post_cable(client, kabeltyp_id=lc.id)

    assert response.status_code == 201, response.text
    cable = response.json()
    assert cable["typ"] == "LC-LC"
    assert cable["kabeltyp_id"] == lc.id
    assert cable["farbe"] == "Erika-Violett"
    assert cable["kabeltyp"] == {
        "id": lc.id,
        "name": "LC-LC",
        "kategorie": "lwl",
        "enden_a": 1,
        "enden_b": 1,
    }


async def test_breakout_typ_schreibt_alt_typ_sonstige(
    client: AsyncClient, db: AsyncSession
):
    breakout = await _seed_breakout(db)

    response = await _post_cable(client, kabeltyp_id=breakout.id)

    assert response.status_code == 201, response.text
    cable = response.json()
    assert cable["typ"] == "sonstige"
    assert cable["kabeltyp_id"] == breakout.id
    assert cable["kabeltyp"]["enden_b"] == 4


async def test_gesetzte_farbe_bleibt_trotz_standardfarbe(
    client: AsyncClient, db: AsyncSession
):
    cat = await _seed_typ(db, "Cat6A", standard_farbe="Blau")

    response = await _post_cable(client, kabeltyp_id=cat.id, farbe="Gelb")

    assert response.status_code == 201, response.text
    assert response.json()["farbe"] == "Gelb"


async def test_nur_typ_setzt_kabeltyp_id_ueber_namen(
    client: AsyncClient, db: AsyncSession
):
    cat = await _seed_typ(db, "Cat6A", standard_farbe="Blau")

    response = await _post_cable(client, typ="Cat6A")

    assert response.status_code == 201, response.text
    cable = response.json()
    assert cable["typ"] == "Cat6A"
    assert cable["kabeltyp_id"] == cat.id
    assert cable["kabeltyp"]["name"] == "Cat6A"


async def test_nur_typ_ohne_katalogzeile_bleibt_ohne_kabeltyp(client: AsyncClient):
    response = await _post_cable(client, typ="Cat7")

    assert response.status_code == 201, response.text
    cable = response.json()
    assert cable["typ"] == "Cat7"
    assert cable["kabeltyp_id"] is None
    assert cable["kabeltyp"] is None


async def test_unbekannte_kabeltyp_id_ergibt_422(client: AsyncClient):
    response = await _post_cable(client, kabeltyp_id=999_999)

    assert response.status_code == 422, response.text


async def test_kabel_ohne_typ_und_ohne_kabeltyp_id_ergibt_422(client: AsyncClient):
    response = await _post_cable(client)

    assert response.status_code == 422, response.text


async def test_update_mit_kabeltyp_id_zieht_typ_nach(
    client: AsyncClient, db: AsyncSession
):
    cat = await _seed_typ(db, "Cat6A", standard_farbe="Blau")
    breakout = await _seed_breakout(db)
    created = (await _post_cable(client, kabeltyp_id=cat.id)).json()

    response = await client.put(
        f"/api/v1/cables/{created['id']}", json={"kabeltyp_id": breakout.id}
    )

    assert response.status_code == 200, response.text
    cable = response.json()
    assert cable["typ"] == "sonstige"
    assert cable["kabeltyp_id"] == breakout.id
    assert cable["farbe"] == "Blau"


async def test_update_mit_unbekannter_kabeltyp_id_ergibt_422(
    client: AsyncClient, db: AsyncSession
):
    cat = await _seed_typ(db, "Cat6A")
    created = (await _post_cable(client, kabeltyp_id=cat.id)).json()

    response = await client.put(
        f"/api/v1/cables/{created['id']}", json={"kabeltyp_id": 999_999}
    )

    assert response.status_code == 422, response.text


async def test_update_nur_typ_zieht_kabeltyp_id_nach(
    client: AsyncClient, db: AsyncSession
):
    cat6a = await _seed_typ(db, "Cat6A")
    cat7 = await _seed_typ(db, "Cat7")
    created = (await _post_cable(client, typ="Cat6A")).json()
    assert created["kabeltyp_id"] == cat6a.id

    response = await client.put(f"/api/v1/cables/{created['id']}", json={"typ": "Cat7"})

    assert response.status_code == 200, response.text
    assert response.json()["typ"] == "Cat7"
    assert response.json()["kabeltyp_id"] == cat7.id


async def test_update_mit_unveraendertem_typ_behaelt_breakout_typ(
    client: AsyncClient, db: AsyncSession
):
    await _seed_typ(db, "sonstige", kategorie="sonstige")
    breakout = await _seed_breakout(db)
    created = (await _post_cable(client, kabeltyp_id=breakout.id)).json()

    # Alter Client schickt das ganze Kabel inklusive unverändertem typ zurück.
    response = await client.put(
        f"/api/v1/cables/{created['id']}",
        json={"typ": "sonstige", "bemerkung": "geprüft"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["kabeltyp_id"] == breakout.id
    assert response.json()["bemerkung"] == "geprüft"


# === Katalogpflege ===========================================================
async def test_katalog_anlegen_lesen_aendern(client: AsyncClient):
    created = await client.post(
        "/api/v1/kabeltypen/",
        json={
            "name": "AOC QSFP28",
            "kategorie": "aoc",
            "stecker_a": "QSFP28",
            "stecker_b": "QSFP28",
            "standard_farbe": "Orange",
        },
    )
    assert created.status_code == 201, created.text
    kabeltyp = created.json()
    assert kabeltyp["enden_a"] == 1
    assert kabeltyp["enden_b"] == 1
    assert kabeltyp["alt_typ"] == "sonstige"
    assert kabeltyp["aktiv"] is True

    updated = await client.put(
        f"/api/v1/kabeltypen/{kabeltyp['id']}", json={"standard_farbe": "Grau"}
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["standard_farbe"] == "Grau"
    assert updated.json()["name"] == "AOC QSFP28"

    listed = await client.get("/api/v1/kabeltypen/")
    assert listed.status_code == 200
    assert [k["name"] for k in listed.json()] == ["AOC QSFP28"]


async def test_katalog_doppelter_name_ergibt_409(client: AsyncClient, db: AsyncSession):
    await _seed_typ(db, "Cat6A")

    response = await client.post(
        "/api/v1/kabeltypen/",
        json={
            "name": "Cat6A",
            "kategorie": "kupfer",
            "stecker_a": "RJ45",
            "stecker_b": "RJ45",
        },
    )

    assert response.status_code == 409, response.text


async def test_katalog_unbekannter_alt_typ_ergibt_422(client: AsyncClient):
    response = await client.post(
        "/api/v1/kabeltypen/",
        json={
            "name": "Fantasie",
            "kategorie": "kupfer",
            "stecker_a": "RJ45",
            "stecker_b": "RJ45",
            "alt_typ": "gibt-es-nicht",
        },
    )

    assert response.status_code == 422, response.text


async def test_verwendeten_typ_loeschen_ergibt_409_mit_anzahl(
    client: AsyncClient, db: AsyncSession
):
    cat = await _seed_typ(db, "Cat6A")
    await _post_cable(client, kabeltyp_id=cat.id)
    await _post_cable(client, kabeltyp_id=cat.id)

    response = await client.delete(f"/api/v1/kabeltypen/{cat.id}")

    assert response.status_code == 409, response.text
    assert "2 Kabel" in response.json()["detail"]
    assert (await client.get("/api/v1/kabeltypen/")).json()[0]["id"] == cat.id


async def test_unbenutzten_typ_loeschen(client: AsyncClient, db: AsyncSession):
    cat = await _seed_typ(db, "Cat6A")

    response = await client.delete(f"/api/v1/kabeltypen/{cat.id}")

    assert response.status_code == 204, response.text
    assert (await client.get("/api/v1/kabeltypen/")).json() == []


async def test_alt_typ_eines_verwendeten_typs_aendern_ergibt_409(
    client: AsyncClient, db: AsyncSession
):
    cat = await _seed_typ(db, "Cat6A")
    await _post_cable(client, kabeltyp_id=cat.id)

    response = await client.put(
        f"/api/v1/kabeltypen/{cat.id}", json={"alt_typ": "Cat7"}
    )

    assert response.status_code == 409, response.text
    assert "1 Kabel" in response.json()["detail"]


async def test_deaktivierter_typ_bleibt_an_kabeln_lesbar(
    client: AsyncClient, db: AsyncSession
):
    cat = await _seed_typ(db, "Cat6A")
    await _seed_typ(db, "Cat7")
    created = (await _post_cable(client, kabeltyp_id=cat.id)).json()

    deactivated = await client.put(
        f"/api/v1/kabeltypen/{cat.id}", json={"aktiv": False}
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["aktiv"] is False

    aktive = await client.get("/api/v1/kabeltypen/", params={"aktiv": "true"})
    assert [k["name"] for k in aktive.json()] == ["Cat7"]
    inaktive = await client.get("/api/v1/kabeltypen/", params={"aktiv": "false"})
    assert [k["name"] for k in inaktive.json()] == ["Cat6A"]
    alle = await client.get("/api/v1/kabeltypen/")
    assert [k["name"] for k in alle.json()] == ["Cat6A", "Cat7"]

    read = await client.get(f"/api/v1/cables/{created['id']}")
    assert read.status_code == 200, read.text
    assert read.json()["kabeltyp_id"] == cat.id
    assert read.json()["kabeltyp"]["name"] == "Cat6A"
    assert read.json()["typ"] == "Cat6A"
