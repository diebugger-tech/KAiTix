"""CSV- und EPLAN-Import ordnen Kabeln den Katalog-Kabeltyp zu.

Regel wie im CablingService: Katalogzeile mit dem Namen des typ. Beim Aktualisieren
bleibt ein gesetzter Kabeltyp, solange sich typ nicht ändert (sonst würde z. B. ein
Breakout mit alt_typ "sonstige" auf die Katalogzeile "sonstige" umgebogen).
"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.cabling.kabeltyp_service import kabeltyp_id_nach_typ
from app.models import Cable, Kabeltyp


async def _seed_typ(
    db: AsyncSession,
    name: str,
    *,
    kategorie: str = "kupfer",
    enden_b: int = 1,
    alt_typ: str | None = None,
) -> Kabeltyp:
    kabeltyp = Kabeltyp(
        name=name,
        kategorie=kategorie,
        stecker_a="RJ45",
        stecker_b="RJ45",
        enden_a=1,
        enden_b=enden_b,
        alt_typ=alt_typ if alt_typ is not None else name,
        aktiv=True,
    )
    db.add(kabeltyp)
    await db.flush()
    return kabeltyp


async def _kabel(db: AsyncSession, kabel_nr: str) -> Cable:
    result = await db.execute(
        select(Cable)
        .where(Cable.kabel_nr == kabel_nr)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


# --- Regel ohne Datenbank ---------------------------------------------------


def test_regel_neues_kabel_nimmt_katalogzeile_gleichen_namens():
    assert kabeltyp_id_nach_typ("Cat6A", {"Cat6A": 7}) == 7


def test_regel_neues_kabel_ohne_passende_katalogzeile_bleibt_ohne_typ():
    assert kabeltyp_id_nach_typ("sonstige", {"Cat6A": 7}) is None


def test_regel_gleicher_typ_behaelt_gesetzten_kabeltyp():
    ids = {"sonstige": 3}
    assert (
        kabeltyp_id_nach_typ("sonstige", ids, alter_typ="sonstige", alte_kabeltyp_id=9)
        == 9
    )


def test_regel_typwechsel_ordnet_neu_zu():
    ids = {"Cat6": 1, "Cat6A": 2}
    assert kabeltyp_id_nach_typ("Cat6A", ids, alter_typ="Cat6", alte_kabeltyp_id=1) == 2


def test_regel_gleicher_typ_ohne_kabeltyp_ordnet_zu():
    ids = {"Cat6": 1}
    assert (
        kabeltyp_id_nach_typ("Cat6", ids, alter_typ="Cat6", alte_kabeltyp_id=None) == 1
    )


# --- CSV-Import ------------------------------------------------------------


async def test_csv_import_setzt_kabeltyp(client: AsyncClient, db: AsyncSession):
    cat6a = await _seed_typ(db, "Cat6A")
    await db.commit()

    resp = await client.post(
        "/api/v1/import-csv/cables/commit",
        json={"rows": [{"row": 1, "kabel_nr": "IMP-1", "typ": "Cat6A"}]},
    )

    assert resp.status_code == 200, resp.text
    kabel = await _kabel(db, "IMP-1")
    assert kabel.typ == "Cat6A"
    assert kabel.kabeltyp_id == cat6a.id


async def test_csv_import_ohne_katalogzeile_bleibt_ohne_kabeltyp(
    client: AsyncClient, db: AsyncSession
):
    await _seed_typ(db, "Cat6A")
    await db.commit()

    resp = await client.post(
        "/api/v1/import-csv/cables/commit",
        json={"rows": [{"row": 1, "kabel_nr": "IMP-2", "typ": "Cat7"}]},
    )

    assert resp.status_code == 200, resp.text
    kabel = await _kabel(db, "IMP-2")
    assert kabel.typ == "Cat7"
    assert kabel.kabeltyp_id is None


async def test_csv_update_typwechsel_ordnet_kabeltyp_neu_zu(
    client: AsyncClient, db: AsyncSession
):
    cat6 = await _seed_typ(db, "Cat6")
    cat6a = await _seed_typ(db, "Cat6A")
    db.add(Cable(kabel_nr="IMP-3", typ="Cat6", kabeltyp_id=cat6.id, laenge_m=1))
    await db.commit()

    resp = await client.post(
        "/api/v1/import-csv/cables/commit",
        json={
            "rows": [{"row": 1, "kabel_nr": "IMP-3", "typ": "Cat6A"}],
            "update_mode": True,
        },
    )

    assert resp.status_code == 200, resp.text
    kabel = await _kabel(db, "IMP-3")
    assert kabel.typ == "Cat6A"
    assert kabel.kabeltyp_id == cat6a.id


async def test_csv_update_gleicher_typ_behaelt_breakout(
    client: AsyncClient, db: AsyncSession
):
    await _seed_typ(db, "sonstige")
    breakout = await _seed_typ(
        db, "Breakout QSFP+→4×SFP+", kategorie="breakout", enden_b=4, alt_typ="sonstige"
    )
    db.add(Cable(kabel_nr="IMP-4", typ="sonstige", kabeltyp_id=breakout.id, laenge_m=3))
    await db.commit()

    resp = await client.post(
        "/api/v1/import-csv/cables/commit",
        json={
            "rows": [{"row": 1, "kabel_nr": "IMP-4", "typ": "sonstige", "laenge_m": 5}],
            "update_mode": True,
        },
    )

    assert resp.status_code == 200, resp.text
    kabel = await _kabel(db, "IMP-4")
    assert kabel.kabeltyp_id == breakout.id
    assert float(kabel.laenge_m) == 5.0


# --- EPLAN-Import ----------------------------------------------------------


def _eplan_verbindung(kabel_nr: str, typ: str) -> dict:
    return {
        "cable_number": kabel_nr,
        "cable_type": typ,
        "length": 2.0,
        "farbe": None,
        "source_rack": "Rack K",
        "source_device": "Switch-K",
        "source_port": "Port 1",
        "target_rack": "Rack K",
        "target_device": "Server-K",
        "target_port": "Eth0",
    }


async def test_eplan_import_setzt_kabeltyp(client: AsyncClient, db: AsyncSession):
    lc = await _seed_typ(db, "LC-LC", kategorie="lwl")
    await db.commit()

    resp = await client.post(
        "/api/v1/import-eplan/commit",
        json={"connections": [_eplan_verbindung("EP-1", "LWL-LC")]},
    )

    assert resp.status_code == 201, resp.text
    kabel = await _kabel(db, "EP-1")
    assert kabel.typ == "LC-LC"
    assert kabel.kabeltyp_id == lc.id


async def test_eplan_update_typwechsel_ordnet_kabeltyp_neu_zu(
    client: AsyncClient, db: AsyncSession
):
    cat6 = await _seed_typ(db, "Cat6")
    cat6a = await _seed_typ(db, "Cat6A")
    db.add(Cable(kabel_nr="EP-2", typ="Cat6", kabeltyp_id=cat6.id, laenge_m=1))
    await db.commit()

    resp = await client.post(
        "/api/v1/import-eplan/commit",
        json={"connections": [_eplan_verbindung("EP-2", "Cat6A")]},
    )

    assert resp.status_code == 201, resp.text
    kabel = await _kabel(db, "EP-2")
    assert kabel.typ == "Cat6A"
    assert kabel.kabeltyp_id == cat6a.id
