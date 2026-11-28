from dataclasses import dataclass

import pytest
from httpx import AsyncClient
from sqlalchemy import event, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.domains.umbau import regeln
from app.domains.umbau.services import UmbauService
from app.models import Cable, Device, Kabeltyp, Rack, UmbauEnde, UmbauEreignis
from tests.conftest import engine

API = "/api/v1/umbau"
HEADERS = {"X-Username": "andreas"}


# === Aufbau ==================================================================
@dataclass
class Szene:
    """Zwei Racks: R1 liegt im Umfang des Umbaus, R2 nicht."""

    rack: Rack
    rack_aussen: Rack
    srv1: Device
    srv2: Device
    sw1: Device
    aussen: Device
    typen: dict[str, Kabeltyp]


async def _szene(db: AsyncSession) -> Szene:
    rack = Rack(name="Umbau-R1", standort="Test")
    rack_aussen = Rack(name="Umbau-R2", standort="Test")
    db.add_all([rack, rack_aussen])
    await db.flush()
    srv1 = Device(hostname="umbau-srv1", typ="server", rack_id=rack.id)
    srv2 = Device(hostname="umbau-srv2", typ="server", rack_id=rack.id)
    sw1 = Device(hostname="umbau-sw1", typ="switch", rack_id=rack.id)
    aussen = Device(hostname="umbau-aussen", typ="switch", rack_id=rack_aussen.id)
    db.add_all([srv1, srv2, sw1, aussen])

    def typ(name, kategorie, enden_b=1, alt_typ=None):
        return Kabeltyp(
            name=name,
            kategorie=kategorie,
            stecker_a="A",
            stecker_b="B",
            enden_a=1,
            enden_b=enden_b,
            alt_typ=alt_typ or name,
            aktiv=True,
        )

    typen = {
        "rj45": typ("Cat6A", "kupfer"),
        "lc": typ("LC-LC", "lwl"),
        "dac": typ("DAC", "dac"),
        "breakout": typ("Breakout QSFP+→4×SFP+", "breakout", 4, "sonstige"),
        "strom": typ("Strom-C13", "strom"),
    }
    db.add_all(typen.values())
    await db.flush()
    return Szene(rack, rack_aussen, srv1, srv2, sw1, aussen, typen)


async def _kabel(client: AsyncClient, kabeltyp: Kabeltyp, **felder) -> dict:
    response = await client.post(
        "/api/v1/cables/", json={"laenge_m": 1, "kabeltyp_id": kabeltyp.id, **felder}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _verbinde(
    client: AsyncClient,
    kabeltyp: Kabeltyp,
    von: Device,
    von_port,
    nach: Device,
    nach_port,
) -> dict:
    return await _kabel(
        client,
        kabeltyp,
        von_device_id=von.id,
        von_port=von_port,
        nach_device_id=nach.id,
        nach_port=nach_port,
    )


async def _umbau(client: AsyncClient, szene: Szene, name: str = "Umbau Test") -> dict:
    response = await client.post(
        f"{API}/", json={"name": name, "rack_ids": [szene.rack.id]}, headers=HEADERS
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _bestaetige_alle(client: AsyncClient, umbau_id: int, szene: Szene) -> None:
    for geraet in (szene.srv1, szene.srv2, szene.sw1):
        response = await client.post(
            f"{API}/{umbau_id}/geraete/{geraet.id}/bestaetigen", headers=HEADERS
        )
        assert response.status_code == 200, response.text


async def _eingefroren(client: AsyncClient, db: AsyncSession) -> tuple[Szene, dict]:
    """Ein Cat6A-Kabel srv1:eth0 ↔ sw1:Gi1, alle Geräte bestätigt, eingefroren."""
    szene = await _szene(db)
    await _verbinde(client, szene.typen["rj45"], szene.srv1, "eth0", szene.sw1, "Gi1")
    umbau = await _umbau(client, szene)
    await _bestaetige_alle(client, umbau["id"], szene)
    response = await client.post(f"{API}/{umbau['id']}/einfrieren", headers=HEADERS)
    assert response.status_code == 200, response.text
    return szene, response.json()


async def _status(client: AsyncClient, umbau_id: int, ziel: str):
    return await client.post(
        f"{API}/{umbau_id}/status", json={"ziel": ziel}, headers=HEADERS
    )


async def _abklemmen(client: AsyncClient, umbau_id: int, ende_id: int, wert=True):
    return await client.put(
        f"{API}/{umbau_id}/enden/{ende_id}/abklemmen",
        params={"abgeklemmt": str(wert).lower()},
        headers=HEADERS,
    )


async def _anklemmen(client: AsyncClient, umbau_id: int, ende_id: int, **body):
    return await client.put(
        f"{API}/{umbau_id}/enden/{ende_id}/anklemmen",
        json={"angeklemmt": True, **body},
        headers=HEADERS,
    )


async def _bis_wiederaufbau(client: AsyncClient, umbau: dict) -> None:
    for ende in umbau["enden"]:
        assert (await _abklemmen(client, umbau["id"], ende["id"])).status_code == 200
    assert (await _status(client, umbau["id"], "umbau")).status_code == 200
    assert (await _status(client, umbau["id"], "wiederaufbau")).status_code == 200


async def _ereignisse(db: AsyncSession, ende_id: int) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(UmbauEreignis)
        .where(UmbauEreignis.ende_id == ende_id)
    )
    return int(result.scalar_one())


# === Regeln (ohne Datenbank) ================================================
def _sicht(**felder) -> regeln.KabelSicht:
    werte = dict(
        id=1,
        kabel_nr="KAB-0001",
        typ="Cat6A",
        kategorie="kupfer",
        kabeltyp_name="Cat6A",
        enden_a=1,
        enden_b=1,
        farbe="Blau",
        von=(1, "eth0"),
        nach=(2, "Gi1"),
    )
    werte.update(felder)
    return regeln.KabelSicht(**werte)


def test_regel_normales_kabel_hat_zwei_enden():
    enden = regeln.enden_fuer_kabel(_sicht())

    assert [(e.seite, e.ende_nr, e.device_id, e.port) for e in enden] == [
        ("A", 1, 1, "eth0"),
        ("B", 1, 2, "Gi1"),
    ]


def test_regel_breakout_hat_ein_a_ende_und_je_strang_ein_b_ende():
    straenge = tuple(
        regeln.StrangSicht(strand_number=n, device_id=10 + n, port=f"sfp{n}")
        for n in (1, 2, 3, 4)
    )
    kabel = _sicht(
        kategorie="breakout", enden_b=4, nach=(None, None), straenge=straenge
    )

    enden = regeln.enden_fuer_kabel(kabel)

    assert len(enden) == 5
    assert [(e.seite, e.ende_nr, e.strand_number) for e in enden[1:]] == [
        ("B", 1, 1),
        ("B", 2, 2),
        ("B", 3, 3),
        ("B", 4, 4),
    ]
    assert regeln.unvollstaendig(kabel) == []


def test_regel_stromkabel_hat_keine_enden_und_liegt_nie_im_umfang():
    strom = _sicht(kategorie="strom", typ="Strom-C13")
    ohne_typ = _sicht(kategorie=None, kabeltyp_name=None, typ="Strom-C19")

    assert regeln.enden_fuer_kabel(strom) == []
    assert regeln.enden_fuer_kabel(ohne_typ) == []
    assert not regeln.im_umfang(strom, {1, 2})


def test_regel_unvollstaendig_nennt_jeden_grund():
    ohne_typ = _sicht(kategorie=None, kabeltyp_name=None)
    ohne_ziel = _sicht(nach=(2, None))
    breakout = _sicht(
        kategorie="breakout",
        enden_b=4,
        nach=(None, None),
        straenge=(regeln.StrangSicht(1, 11, "sfp1"), regeln.StrangSicht(2, None, None)),
    )

    assert regeln.unvollstaendig(ohne_typ) == ["Kabeltyp fehlt"]
    assert regeln.unvollstaendig(_sicht(von=(None, "eth0"))) == [
        "A-Ende fehlt (Gerät oder Port)"
    ]
    assert regeln.unvollstaendig(_sicht(enden_a=2)) == [
        "Kabeltyp mit 2 A-Enden wird im Umbau nicht unterstützt"
    ]
    assert regeln.unvollstaendig(_sicht(kategorie="strom", nach=(None, None))) == []
    assert regeln.unvollstaendig(ohne_ziel) == ["Gegenstelle fehlt (Gerät oder Port)"]
    assert regeln.unvollstaendig(breakout) == [
        "B-Enden fehlen (2 von 4 Strängen)",
        "B-Enden fehlen (Gerät oder Port an Ende 2)",
    ]


def test_regel_umfang_braucht_ein_ende_an_einem_geraet_im_umfang():
    kabel = _sicht(von=(1, "eth0"), nach=(99, "Gi1"))

    assert regeln.im_umfang(kabel, {1})
    assert regeln.im_umfang(kabel, {99})
    assert not regeln.im_umfang(kabel, {5})


@pytest.mark.parametrize(
    "aktion, ende_status, umbau_status, erlaubt",
    [
        (regeln.ABKLEMMEN, "gesteckt", "rueckbau", True),
        (regeln.ABKLEMMEN, "gesteckt", "erfassung", False),
        (regeln.ABKLEMMEN, "gesteckt", "wiederaufbau", False),
        (regeln.ABKLEMMEN_ZURUECK, "abgeklemmt", "rueckbau", True),
        (regeln.ABKLEMMEN_ZURUECK, "abgeklemmt", "wiederaufbau", False),
        (regeln.ANKLEMMEN, "abgeklemmt", "wiederaufbau", True),
        (regeln.ANKLEMMEN, "abgeklemmt", "rueckbau", False),
        (regeln.ANKLEMMEN, "gesteckt", "wiederaufbau", False),
        (regeln.ANKLEMMEN_ABWEICHEND, "angeklemmt", "wiederaufbau", False),
        (regeln.ANKLEMMEN_ZURUECK, "angeklemmt_abweichend", "wiederaufbau", True),
        (regeln.ANKLEMMEN_ZURUECK, "gesteckt", "wiederaufbau", False),
    ],
)
def test_regel_uebergaenge_eines_endes(aktion, ende_status, umbau_status, erlaubt):
    grund = regeln.aktion_sperrgrund(aktion, ende_status, umbau_status)

    assert (grund is None) == erlaubt


def test_regel_sperrgrund_je_ende_folgt_dem_status_des_umbaus():
    assert regeln.sperrgrund("gesteckt", "rueckbau") is None
    assert regeln.sperrgrund("abgeklemmt", "rueckbau") is None
    assert regeln.sperrgrund("abgeklemmt", "umbau") is not None
    assert regeln.sperrgrund("abgeklemmt", "wiederaufbau") is None
    assert regeln.sperrgrund("angeklemmt", "wiederaufbau") is None
    assert regeln.sperrgrund("gesteckt", "wiederaufbau") is not None
    assert regeln.sperrgrund("angeklemmt", "abgeschlossen") is not None


def test_regel_statuswechsel_des_umbaus():
    wechsel = regeln.umbau_uebergang_sperrgrund

    assert wechsel("erfassung", "rueckbau", {}) is None
    assert "Kabel X" in wechsel(
        "erfassung", "rueckbau", {}, ["Kabel X: Kabeltyp fehlt"]
    )
    assert wechsel("rueckbau", "umbau", {"abgeklemmt": 3}) is None
    assert "1 Ende ist noch gesteckt" in wechsel(
        "rueckbau", "umbau", {"gesteckt": 1, "abgeklemmt": 2}
    )
    assert wechsel("umbau", "wiederaufbau", {"abgeklemmt": 3}) is None
    assert wechsel("wiederaufbau", "abgeschlossen", {"angeklemmt": 3}) is None
    assert wechsel("wiederaufbau", "abgeschlossen", {"abgeklemmt": 1}) is not None
    assert wechsel("rueckbau", "wiederaufbau", {}) is not None
    assert wechsel("umbau", "rueckbau", {}) is not None
    for status in ("erfassung", "rueckbau", "umbau", "wiederaufbau", "verworfen"):
        assert wechsel(status, "verworfen", {}) is None
    assert wechsel("abgeschlossen", "verworfen", {}) is not None


# === Anlegen, Umfang, Bestätigen =============================================
async def test_umbau_anlegen_listen_und_umfang(client: AsyncClient, db: AsyncSession):
    szene = await _szene(db)
    await _verbinde(client, szene.typen["rj45"], szene.srv1, "eth0", szene.sw1, "Gi1")
    # Ein Ende im Umfang genügt: das andere Gerät steht in R2.
    await _verbinde(client, szene.typen["lc"], szene.srv2, "fc0", szene.aussen, "Te1")
    # Ganz außerhalb und Strom zählen nicht.
    await _kabel(
        client,
        szene.typen["rj45"],
        von_device_id=szene.aussen.id,
        von_port="Gi7",
        nach_device_id=szene.aussen.id,
        nach_port="Gi8",
    )
    await _verbinde(client, szene.typen["strom"], szene.srv1, "PSU1", szene.sw1, "A1")

    umbau = await _umbau(client, szene)

    assert umbau["status"] == "erfassung"
    assert umbau["erstellt_von"] == "andreas"
    assert umbau["racks"] == [{"id": szene.rack.id, "name": "Umbau-R1"}]
    geraete = {g["hostname"]: g for g in umbau["geraete"]}
    assert set(geraete) == {"umbau-srv1", "umbau-srv2", "umbau-sw1"}
    assert geraete["umbau-srv1"]["kabel_gesamt"] == 1
    assert geraete["umbau-srv2"]["kabel_gesamt"] == 1
    assert geraete["umbau-srv1"]["bestaetigt"] is False
    assert umbau["enden"] == []

    liste = await client.get(f"{API}/")
    assert liste.status_code == 200, liste.text
    eintrag = next(u for u in liste.json() if u["id"] == umbau["id"])
    assert eintrag["geraete_gesamt"] == 3
    assert eintrag["geraete_bestaetigt"] == 0


async def test_umbau_mit_unbekanntem_rack_ergibt_422(client: AsyncClient):
    response = await client.post(
        f"{API}/", json={"name": "X", "rack_ids": [999_999]}, headers=HEADERS
    )

    assert response.status_code == 422, response.text


async def test_geraet_bestaetigen_ist_idempotent_und_ruecknehmbar(
    client: AsyncClient, db: AsyncSession
):
    szene = await _szene(db)
    umbau = await _umbau(client, szene)
    url = f"{API}/{umbau['id']}/geraete/{szene.srv1.id}/bestaetigen"

    erste = await client.post(url, headers=HEADERS)
    zweite = await client.post(url, headers=HEADERS)
    assert erste.status_code == 200, erste.text
    assert zweite.status_code == 200, zweite.text
    assert erste.json()["bestaetigt"] is True
    assert erste.json()["bestaetigt_von"] == "andreas"
    assert zweite.json()["bestaetigt_am"] == erste.json()["bestaetigt_am"]

    zurueck = await client.post(url, params={"bestaetigt": "false"}, headers=HEADERS)
    nochmal = await client.post(url, params={"bestaetigt": "false"}, headers=HEADERS)
    assert zurueck.json()["bestaetigt"] is False
    assert nochmal.status_code == 200, nochmal.text

    fremd = await client.post(
        f"{API}/{umbau['id']}/geraete/{szene.aussen.id}/bestaetigen", headers=HEADERS
    )
    assert fremd.status_code == 409, fremd.text


async def test_geraet_bestaetigen_nur_in_der_erfassung(
    client: AsyncClient, db: AsyncSession
):
    szene, umbau = await _eingefroren(client, db)

    response = await client.post(
        f"{API}/{umbau['id']}/geraete/{szene.srv1.id}/bestaetigen",
        params={"bestaetigt": "false"},
        headers=HEADERS,
    )

    assert response.status_code == 409, response.text


# === Einfrieren ==============================================================
async def test_einfrieren_erzeugt_enden_je_kabeltyp(
    client: AsyncClient, db: AsyncSession
):
    szene = await _szene(db)
    rj45 = await _verbinde(
        client, szene.typen["rj45"], szene.srv1, "eth0", szene.sw1, "Gi1"
    )
    lc = await _verbinde(client, szene.typen["lc"], szene.srv1, "fc0", szene.sw1, "Te1")
    dac = await _verbinde(
        client, szene.typen["dac"], szene.srv2, "p1", szene.sw1, "Te2"
    )
    strom = await _verbinde(
        client, szene.typen["strom"], szene.srv1, "PSU1", szene.sw1, "A1"
    )
    breakout = await _kabel(
        client,
        szene.typen["breakout"],
        von_device_id=szene.sw1.id,
        von_port="qsfp1",
        farbe="Schwarz",
        straenge=[
            {"strand_number": 1, "nach_device_id": szene.srv1.id, "nach_port": "s1"},
            {"strand_number": 2, "nach_device_id": szene.srv1.id, "nach_port": "s2"},
            {"strand_number": 3, "nach_device_id": szene.srv2.id, "nach_port": "s3"},
            {"strand_number": 4, "nach_device_id": szene.aussen.id, "nach_port": "s4"},
        ],
    )
    umbau = await _umbau(client, szene)
    await _bestaetige_alle(client, umbau["id"], szene)

    response = await client.post(f"{API}/{umbau['id']}/einfrieren", headers=HEADERS)

    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["status"] == "rueckbau"
    assert detail["eingefroren_von"] == "andreas"
    je_kabel: dict[int, list[dict]] = {}
    for ende in detail["enden"]:
        je_kabel.setdefault(ende["cable_id"], []).append(ende)
    assert len(je_kabel[rj45["id"]]) == 2
    assert len(je_kabel[lc["id"]]) == 2
    assert len(je_kabel[dac["id"]]) == 2
    assert len(je_kabel[breakout["id"]]) == 5
    assert strom["id"] not in je_kabel
    assert detail["fortschritt"] == {
        "enden_gesamt": 11,
        "gesteckt": 11,
        "abgeklemmt": 0,
        "angeklemmt": 0,
        "abweichend": 0,
    }

    b_enden = sorted(
        (e for e in je_kabel[breakout["id"]] if e["seite"] == "B"),
        key=lambda e: e["ende_nr"],
    )
    assert [e["strand_number"] for e in b_enden] == [1, 2, 3, 4]
    assert [e["soll_port"] for e in b_enden] == ["s1", "s2", "s3", "s4"]
    assert b_enden[3]["soll_device_name"] == "umbau-aussen"
    assert b_enden[3]["soll_rack_name"] == "Umbau-R2"
    assert b_enden[0]["gegenseite"] == ["umbau-sw1:qsfp1"]
    a_ende = next(e for e in je_kabel[breakout["id"]] if e["seite"] == "A")
    assert a_ende["kabeltyp_name"] == "Breakout QSFP+→4×SFP+"
    assert a_ende["kategorie"] == "breakout"
    assert a_ende["farbe"] == "Schwarz"
    assert len(a_ende["gegenseite"]) == 4
    assert all(e["status"] == "gesteckt" and e["sperrgrund"] is None for e in b_enden)

    # Zweites Einfrieren: Ziel schon erreicht, keine doppelten Enden.
    nochmal = await client.post(f"{API}/{umbau['id']}/einfrieren", headers=HEADERS)
    assert nochmal.status_code == 200, nochmal.text
    assert len(nochmal.json()["enden"]) == 11


async def test_einfrieren_mit_unvollstaendigem_kabel_nennt_das_kabel(
    client: AsyncClient, db: AsyncSession
):
    szene = await _szene(db)
    await _kabel(
        client,
        szene.typen["rj45"],
        kabel_nr="KAB-OFFEN",
        von_device_id=szene.srv1.id,
        von_port="eth0",
    )
    await _kabel(
        client,
        szene.typen["breakout"],
        kabel_nr="KAB-BREAK",
        von_device_id=szene.sw1.id,
        von_port="qsfp1",
        straenge=[
            {"strand_number": 1, "nach_device_id": szene.srv1.id, "nach_port": "s1"},
            {"strand_number": 2},
            {"strand_number": 3},
            {"strand_number": 4},
        ],
    )
    umbau = await _umbau(client, szene)
    await _bestaetige_alle(client, umbau["id"], szene)

    response = await client.post(f"{API}/{umbau['id']}/einfrieren", headers=HEADERS)

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert "KAB-OFFEN" in detail and "Gegenstelle fehlt" in detail
    assert "KAB-BREAK" in detail and "B-Enden fehlen" in detail

    gelesen = (await client.get(f"{API}/{umbau['id']}")).json()
    assert gelesen["status"] == "erfassung"
    assert len(gelesen["einfrier_sperren"]) == 2
    sperre = next(z for z in gelesen["naechste_status"] if z["ziel"] == "rueckbau")
    assert "KAB-OFFEN" in sperre["sperrgrund"]


async def test_einfrieren_mit_unbestaetigtem_geraet_nennt_das_geraet(
    client: AsyncClient, db: AsyncSession
):
    szene = await _szene(db)
    await _verbinde(client, szene.typen["rj45"], szene.srv1, "eth0", szene.sw1, "Gi1")
    umbau = await _umbau(client, szene)
    for geraet in (szene.srv1, szene.sw1):
        await client.post(
            f"{API}/{umbau['id']}/geraete/{geraet.id}/bestaetigen", headers=HEADERS
        )

    response = await client.post(f"{API}/{umbau['id']}/einfrieren", headers=HEADERS)

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert "umbau-srv2" in detail
    assert "umbau-srv1" not in detail


async def test_soll_bleibt_nach_kabelaenderung_und_geraeteloeschung(
    client: AsyncClient, db: AsyncSession
):
    szene, umbau = await _eingefroren(client, db)
    cable_id = umbau["enden"][0]["cable_id"]
    vorher = {e["id"]: e for e in umbau["enden"]}

    geaendert = await client.put(
        f"/api/v1/cables/{cable_id}",
        json={"von_port": "eth9", "nach_port": "Gi99", "farbe": "Gelb"},
    )
    assert geaendert.status_code == 200, geaendert.text
    await db.delete(await db.get(Device, szene.srv1.id))
    await db.commit()

    nachher = (await client.get(f"{API}/{umbau['id']}")).json()["enden"]

    assert len(nachher) == 2
    for ende in nachher:
        alt = vorher[ende["id"]]
        for feld in (
            "soll_device_name",
            "soll_rack_name",
            "soll_port",
            "kabel_nr",
            "kabeltyp_name",
            "kategorie",
            "farbe",
        ):
            assert ende[feld] == alt[feld], feld
    a_ende = next(e for e in nachher if e["seite"] == "A")
    assert a_ende["soll_device_name"] == "umbau-srv1"
    assert a_ende["soll_port"] == "eth0"
    assert a_ende["soll_device_id"] is None  # Gerät gelöscht, Textkopie bleibt

    await db.delete(await db.get(Cable, cable_id))
    await db.commit()
    ohne_kabel = (await client.get(f"{API}/{umbau['id']}")).json()["enden"]
    assert [e["cable_id"] for e in ohne_kabel] == [None, None]
    assert {e["soll_port"] for e in ohne_kabel} == {"eth0", "Gi1"}
    assert ohne_kabel[0]["gegenseite"]  # über die Kabelnummer weiter auffindbar


# === Abklemmen ===============================================================
async def test_abklemmen_in_der_erfassung_ergibt_409(
    client: AsyncClient, db: AsyncSession
):
    szene = await _szene(db)
    umbau = await _umbau(client, szene)

    response = await _abklemmen(client, umbau["id"], 1)

    assert response.status_code == 409, response.text
    assert "Rückbau" in response.json()["detail"]


async def test_abklemmen_im_wiederaufbau_ergibt_409(
    client: AsyncClient, db: AsyncSession
):
    _, umbau = await _eingefroren(client, db)
    await _bis_wiederaufbau(client, umbau)

    response = await _abklemmen(client, umbau["id"], umbau["enden"][0]["id"])

    assert response.status_code == 409, response.text
    assert "Wiederaufbau" in response.json()["detail"]


async def test_doppeltes_abklemmen_ergibt_200_ohne_zweites_ereignis(
    client: AsyncClient, db: AsyncSession
):
    _, umbau = await _eingefroren(client, db)
    ende_id = umbau["enden"][0]["id"]

    erste = await _abklemmen(client, umbau["id"], ende_id)
    zweite = await _abklemmen(client, umbau["id"], ende_id)

    assert erste.status_code == 200, erste.text
    assert erste.json()["status"] == "abgeklemmt"
    assert erste.json()["abgeklemmt_von"] == "andreas"
    assert zweite.status_code == 200, zweite.text
    assert zweite.json()["abgeklemmt_am"] == erste.json()["abgeklemmt_am"]
    assert await _ereignisse(db, ende_id) == 1


async def test_abklemmen_zuruecknehmen_geht_genau_eine_stufe(
    client: AsyncClient, db: AsyncSession
):
    _, umbau = await _eingefroren(client, db)
    ende_id = umbau["enden"][0]["id"]
    await _abklemmen(client, umbau["id"], ende_id)

    zurueck = await _abklemmen(client, umbau["id"], ende_id, wert=False)
    nochmal = await _abklemmen(client, umbau["id"], ende_id, wert=False)

    assert zurueck.status_code == 200, zurueck.text
    assert zurueck.json()["status"] == "gesteckt"
    assert zurueck.json()["abgeklemmt_am"] is None
    assert nochmal.status_code == 200, nochmal.text
    assert await _ereignisse(db, ende_id) == 2


async def test_rowcount_0_ziel_schon_erreicht_ergibt_200_ohne_ereignis(
    client: AsyncClient, db: AsyncSession
):
    _, umbau = await _eingefroren(client, db)
    ende_id = umbau["enden"][0]["id"]
    # Das geladene Objekt bleibt in der Session und zeigt weiter "gesteckt",
    # während die Zeile direkt in der DB umgesetzt wird. So liest der Service
    # einen veralteten Stand, sein bedingtes UPDATE trifft keine Zeile.
    veraltet = (
        await db.execute(select(UmbauEnde).where(UmbauEnde.id == ende_id))
    ).scalar_one()
    await db.execute(
        text("UPDATE umbau_enden SET status = 'abgeklemmt' WHERE id = :id"),
        {"id": ende_id},
    )
    assert veraltet.status == "gesteckt"

    response = await _abklemmen(client, umbau["id"], ende_id)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "abgeklemmt"
    assert await _ereignisse(db, ende_id) == 0


async def test_rowcount_0_anderer_stand_ergibt_409_ohne_ereignis(
    client: AsyncClient, db: AsyncSession
):
    _, umbau = await _eingefroren(client, db)
    ende_id = umbau["enden"][0]["id"]
    veraltet = (
        await db.execute(select(UmbauEnde).where(UmbauEnde.id == ende_id))
    ).scalar_one()
    await db.execute(
        text("UPDATE umbau_enden SET status = 'angeklemmt' WHERE id = :id"),
        {"id": ende_id},
    )
    assert veraltet.status == "gesteckt"

    response = await _abklemmen(client, umbau["id"], ende_id)

    assert response.status_code == 409, response.text
    assert await _ereignisse(db, ende_id) == 0
    gelesen = (await client.get(f"{API}/{umbau['id']}")).json()
    assert next(e for e in gelesen["enden"] if e["id"] == ende_id)["status"] == (
        "angeklemmt"
    )


# === Statuswechsel ===========================================================
async def test_rueckbau_nach_umbau_mit_gestecktem_ende_ergibt_409(
    client: AsyncClient, db: AsyncSession
):
    _, umbau = await _eingefroren(client, db)
    await _abklemmen(client, umbau["id"], umbau["enden"][0]["id"])

    response = await _status(client, umbau["id"], "umbau")

    assert response.status_code == 409, response.text
    assert "1 Ende ist noch gesteckt" in response.json()["detail"]

    await _abklemmen(client, umbau["id"], umbau["enden"][1]["id"])
    erlaubt = await _status(client, umbau["id"], "umbau")
    assert erlaubt.status_code == 200, erlaubt.text
    assert erlaubt.json()["status"] == "umbau"
    assert all(e["sperrgrund"] for e in erlaubt.json()["enden"])


async def test_abschluss_mit_offenem_ende_ergibt_409(
    client: AsyncClient, db: AsyncSession
):
    _, umbau = await _eingefroren(client, db)
    await _bis_wiederaufbau(client, umbau)
    erstes, zweites = (ende["id"] for ende in umbau["enden"])
    assert (await _anklemmen(client, umbau["id"], erstes)).status_code == 200

    offen = await _status(client, umbau["id"], "abgeschlossen")
    assert offen.status_code == 409, offen.text
    assert "1 Ende ist noch nicht angeklemmt" in offen.json()["detail"]

    assert (await _anklemmen(client, umbau["id"], zweites)).status_code == 200
    fertig = await _status(client, umbau["id"], "abgeschlossen")
    assert fertig.status_code == 200, fertig.text
    assert fertig.json()["status"] == "abgeschlossen"
    assert fertig.json()["abgeschlossen_von"] == "andreas"
    assert fertig.json()["naechste_status"] == []

    verwerfen = await _status(client, umbau["id"], "verworfen")
    assert verwerfen.status_code == 409, verwerfen.text


async def test_statuswechsel_ist_idempotent_und_kennt_keine_spruenge(
    client: AsyncClient, db: AsyncSession
):
    _, umbau = await _eingefroren(client, db)

    gleich = await _status(client, umbau["id"], "rueckbau")
    sprung = await _status(client, umbau["id"], "wiederaufbau")
    verworfen = await _status(client, umbau["id"], "verworfen")

    assert gleich.status_code == 200, gleich.text
    assert sprung.status_code == 409, sprung.text
    assert verworfen.status_code == 200, verworfen.text
    assert verworfen.json()["status"] == "verworfen"
    wechsel = [
        e["nach_status"] for e in verworfen.json()["ereignisse"] if e["ende_id"] is None
    ]
    assert wechsel == ["verworfen", "rueckbau", "erfassung"]


async def test_status_rueckbau_aus_der_erfassung_friert_ein(
    client: AsyncClient, db: AsyncSession
):
    szene = await _szene(db)
    await _verbinde(client, szene.typen["rj45"], szene.srv1, "eth0", szene.sw1, "Gi1")
    umbau = await _umbau(client, szene)

    gesperrt = await _status(client, umbau["id"], "rueckbau")
    assert gesperrt.status_code == 409, gesperrt.text
    assert "umbau-srv1" in gesperrt.json()["detail"]

    await _bestaetige_alle(client, umbau["id"], szene)
    response = await _status(client, umbau["id"], "rueckbau")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "rueckbau"
    assert len(response.json()["enden"]) == 2


async def test_unbekannter_umbau_ergibt_404(client: AsyncClient):
    assert (await client.get(f"{API}/999999")).status_code == 404
    assert (await _status(client, 999_999, "umbau")).status_code == 404
    assert (await _abklemmen(client, 999_999, 1)).status_code == 404


def _veralteter_umbau(monkeypatch, status: str) -> None:
    """Der Service liest beim ersten Zugriff einen veralteten Status.

    So lässt sich nachstellen, dass zwischen Lesen und bedingtem UPDATE jemand
    anderes den Umbau weitergeschaltet hat (rowcount 0).
    """
    original = UmbauService.get_umbau
    aufrufe = {"anzahl": 0}

    async def get_umbau(self, umbau_id):
        umbau = await original(self, umbau_id)
        aufrufe["anzahl"] += 1
        if aufrufe["anzahl"] == 1:
            set_committed_value(umbau, "status", status)
        return umbau

    monkeypatch.setattr(UmbauService, "get_umbau", get_umbau)


async def _status_ereignisse(db: AsyncSession, umbau_id: int, nach: str) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(UmbauEreignis)
        .where(
            UmbauEreignis.umbau_id == umbau_id,
            UmbauEreignis.ende_id.is_(None),
            UmbauEreignis.nach_status == nach,
        )
    )
    return int(result.scalar_one())


async def test_statuswechsel_rowcount_0_ziel_schon_erreicht_ergibt_200(
    client: AsyncClient, db: AsyncSession, monkeypatch
):
    _, umbau = await _eingefroren(client, db)
    for ende in umbau["enden"]:
        await _abklemmen(client, umbau["id"], ende["id"])
    await db.execute(
        text("UPDATE umbauten SET status = 'umbau' WHERE id = :id"), {"id": umbau["id"]}
    )
    _veralteter_umbau(monkeypatch, "rueckbau")

    response = await _status(client, umbau["id"], "umbau")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "umbau"
    assert await _status_ereignisse(db, umbau["id"], "umbau") == 0


async def test_statuswechsel_rowcount_0_anderer_stand_ergibt_409(
    client: AsyncClient, db: AsyncSession, monkeypatch
):
    _, umbau = await _eingefroren(client, db)
    for ende in umbau["enden"]:
        await _abklemmen(client, umbau["id"], ende["id"])
    await db.execute(
        text("UPDATE umbauten SET status = 'verworfen' WHERE id = :id"),
        {"id": umbau["id"]},
    )
    _veralteter_umbau(monkeypatch, "rueckbau")

    response = await _status(client, umbau["id"], "umbau")

    assert response.status_code == 409, response.text
    assert await _status_ereignisse(db, umbau["id"], "umbau") == 0
    assert (await client.get(f"{API}/{umbau['id']}")).json()["status"] == "verworfen"


async def test_einfrieren_rowcount_0_ziel_schon_erreicht_legt_keine_enden_doppelt_an(
    client: AsyncClient, db: AsyncSession, monkeypatch
):
    _, umbau = await _eingefroren(client, db)
    # Zweiter Einfrier-Aufruf, der noch "erfassung" gelesen hat.
    _veralteter_umbau(monkeypatch, "erfassung")

    response = await client.post(f"{API}/{umbau['id']}/einfrieren", headers=HEADERS)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "rueckbau"
    assert len(response.json()["enden"]) == 2
    assert await _status_ereignisse(db, umbau["id"], "rueckbau") == 1


# === Anklemmen ===============================================================
async def test_anklemmen_nach_soll(client: AsyncClient, db: AsyncSession):
    _, umbau = await _eingefroren(client, db)
    await _bis_wiederaufbau(client, umbau)
    ende_id = umbau["enden"][0]["id"]

    erste = await _anklemmen(client, umbau["id"], ende_id)
    zweite = await _anklemmen(client, umbau["id"], ende_id)

    assert erste.status_code == 200, erste.text
    assert erste.json()["status"] == "angeklemmt"
    assert erste.json()["ist_port"] is None
    assert zweite.status_code == 200, zweite.text
    assert await _ereignisse(db, ende_id) == 2  # abgeklemmt + angeklemmt


async def test_anklemmen_an_anderem_port_braucht_einen_grund(
    client: AsyncClient, db: AsyncSession
):
    szene, umbau = await _eingefroren(client, db)
    await _bis_wiederaufbau(client, umbau)
    ende = next(e for e in umbau["enden"] if e["seite"] == "A")

    ohne_grund = await _anklemmen(client, umbau["id"], ende["id"], ist_port="eth5")
    leerer_grund = await _anklemmen(
        client, umbau["id"], ende["id"], ist_port="eth5", grund="   "
    )
    assert ohne_grund.status_code == 422, ohne_grund.text
    assert leerer_grund.status_code == 422, leerer_grund.text

    mit_grund = await _anklemmen(
        client,
        umbau["id"],
        ende["id"],
        ist_device_id=szene.srv2.id,
        ist_port="eth5",
        grund="Port eth0 defekt",
    )

    assert mit_grund.status_code == 200, mit_grund.text
    gebucht = mit_grund.json()
    assert gebucht["status"] == "angeklemmt_abweichend"
    assert gebucht["ist_device_name"] == "umbau-srv2"
    assert gebucht["ist_port"] == "eth5"
    assert gebucht["abweichung_grund"] == "Port eth0 defekt"
    assert gebucht["soll_port"] == "eth0"  # Soll bleibt

    # Gleiche Meldung noch einmal: Ziel schon erreicht.
    gleich = await _anklemmen(
        client,
        umbau["id"],
        ende["id"],
        ist_device_id=szene.srv2.id,
        ist_port="eth5",
        grund="Port eth0 defekt",
    )
    assert gleich.status_code == 200, gleich.text
    # Ein anderer Port ohne vorherige Rücknahme geht nicht.
    woanders = await _anklemmen(
        client, umbau["id"], ende["id"], ist_port="eth7", grund="doch anders"
    )
    assert woanders.status_code == 409, woanders.text
    detail = (await client.get(f"{API}/{umbau['id']}")).json()
    assert detail["fortschritt"]["abweichend"] == 1
    assert detail["fortschritt"]["angeklemmt"] == 1


async def test_anklemmen_zuruecknehmen_geht_genau_eine_stufe(
    client: AsyncClient, db: AsyncSession
):
    _, umbau = await _eingefroren(client, db)
    await _bis_wiederaufbau(client, umbau)
    ende_id = umbau["enden"][0]["id"]
    await _anklemmen(client, umbau["id"], ende_id, ist_port="eth5", grund="defekt")

    zurueck = await client.put(
        f"{API}/{umbau['id']}/enden/{ende_id}/anklemmen",
        json={"angeklemmt": False},
        headers=HEADERS,
    )
    nochmal = await client.put(
        f"{API}/{umbau['id']}/enden/{ende_id}/anklemmen",
        json={"angeklemmt": False},
        headers=HEADERS,
    )

    assert zurueck.status_code == 200, zurueck.text
    ende = zurueck.json()
    assert ende["status"] == "abgeklemmt"  # eine Stufe, nicht bis "gesteckt"
    assert ende["angeklemmt_am"] is None
    assert ende["ist_port"] is None
    assert ende["abweichung_grund"] is None
    assert ende["abgeklemmt_am"] is not None
    assert nochmal.status_code == 200, nochmal.text
    assert nochmal.json()["status"] == "abgeklemmt"
    # Abklemmen zurücknehmen ist im Wiederaufbau nicht vorgesehen.
    weiter = await _abklemmen(client, umbau["id"], ende_id, wert=False)
    assert weiter.status_code == 409, weiter.text


async def test_anklemmen_im_rueckbau_ergibt_409(client: AsyncClient, db: AsyncSession):
    _, umbau = await _eingefroren(client, db)

    response = await _anklemmen(client, umbau["id"], umbau["enden"][0]["id"])

    assert response.status_code == 409, response.text


async def test_fremdes_ende_ergibt_404(client: AsyncClient, db: AsyncSession):
    _, umbau = await _eingefroren(client, db)

    response = await _abklemmen(client, umbau["id"], 999_999)

    assert response.status_code == 404, response.text


# === Schreibsperre ===========================================================
async def test_nach_dem_einfrieren_schreibt_der_umbau_nicht_in_die_kabelliste(
    client: AsyncClient, db: AsyncSession
):
    _, umbau = await _eingefroren(client, db)
    geschuetzt = ("cables", "cable_strands", "interfaces")
    schreibzugriffe: list[str] = []

    def mitschreiben(conn, cursor, statement, parameters, context, executemany):
        sql = " ".join(statement.split()).lower()
        for tabelle in geschuetzt:
            if (
                sql.startswith(f"insert into {tabelle} ")
                or sql.startswith(f"update {tabelle} ")
                or sql.startswith(f"delete from {tabelle} ")
            ):
                schreibzugriffe.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", mitschreiben)
    try:
        erstes, zweites = (ende["id"] for ende in umbau["enden"])
        await _abklemmen(client, umbau["id"], erstes)
        await _abklemmen(client, umbau["id"], erstes, wert=False)
        await _bis_wiederaufbau(client, umbau)
        await _anklemmen(client, umbau["id"], erstes)
        await _anklemmen(client, umbau["id"], zweites, ist_port="x9", grund="Test")
        await client.put(
            f"{API}/{umbau['id']}/enden/{zweites}/anklemmen",
            json={"angeklemmt": False},
            headers=HEADERS,
        )
        await _anklemmen(client, umbau["id"], zweites)
        fertig = await _status(client, umbau["id"], "abgeschlossen")
        await client.get(f"{API}/{umbau['id']}")
        await client.get(f"{API}/")
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", mitschreiben)

    assert fertig.status_code == 200, fertig.text
    assert schreibzugriffe == []
