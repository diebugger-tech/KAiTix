"""Korrekturen am Umbau aus der Analyse vom 27.11.:

- Kabel ohne Kabelnummer sperren das Einfrieren (Frage 3)
- Port-Vergleich beim Anklemmen ohne Groß-/Kleinschreibung (Frage 4)
- Soll-Kopie mit HE-Position und Länge (Frage 1)
- Unbekanntes Kabel im Rückbau nachtragen und wieder entfernen (Frage 7)
"""

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.umbau import regeln
from app.models import Cable, Device, UmbauEnde, UmbauEreignis
from tests.test_umbau import (
    API,
    HEADERS,
    _abklemmen,
    _anklemmen,
    _bestaetige_alle,
    _bis_wiederaufbau,
    _eingefroren,
    _sicht,
    _status,
    _szene,
    _umbau,
    _verbinde,
)


# === Regeln (ohne Datenbank) ================================================
def test_regel_kabel_ohne_nummer_ist_unvollstaendig():
    assert regeln.unvollstaendig(_sicht(kabel_nr=None)) == ["Kabelnummer fehlt"]
    assert regeln.unvollstaendig(_sicht(kabel_nr="  ")) == ["Kabelnummer fehlt"]
    assert regeln.unvollstaendig(_sicht(kabel_nr=None, kategorie="strom")) == []


def test_regel_port_vergleich_ohne_gross_kleinschreibung():
    soll = (1, "Gi1/0/1")

    assert not regeln.ist_abweichung(soll, None, "gi1/0/1")
    assert not regeln.ist_abweichung(soll, 1, " GI1/0/1 ")
    assert regeln.ist_abweichung(soll, 1, "Gi1/0/2")
    assert regeln.ist_abweichung(soll, 2, "gi1/0/1")


def test_regel_position_als_text():
    assert regeln.position_text(12, 1, None) == "HE 12"
    assert regeln.position_text(12, 2, None) == "HE 12–13"
    assert regeln.position_text(None, 0, "left") == "0U links"
    assert regeln.position_text(None, 0, "right") == "0U rechts"
    assert regeln.position_text(None, 1, None) is None


def test_regel_nachtragen_nur_im_rueckbau():
    assert regeln.nachtrag_sperrgrund(regeln.RUECKBAU) is None
    for status in (
        regeln.ERFASSUNG,
        regeln.UMBAU,
        regeln.WIEDERAUFBAU,
        regeln.ABGESCHLOSSEN,
        regeln.VERWORFEN,
    ):
        assert regeln.nachtrag_sperrgrund(status)


def test_regel_nachtrag_entfernen_nur_solange_alles_gesteckt():
    gesteckt = [regeln.GESTECKT, regeln.GESTECKT]

    assert regeln.nachtrag_entfernen_sperrgrund(regeln.RUECKBAU, gesteckt) is None
    assert regeln.nachtrag_entfernen_sperrgrund(
        regeln.RUECKBAU, [regeln.GESTECKT, regeln.ABGEKLEMMT]
    )
    assert regeln.nachtrag_entfernen_sperrgrund(regeln.UMBAU, gesteckt)


# === Kabelnummer (Frage 3) ==================================================
async def test_einfrieren_mit_kabel_ohne_nummer_ergibt_409(
    client: AsyncClient, db: AsyncSession
):
    szene = await _szene(db)
    kabel = await _verbinde(
        client, szene.typen["rj45"], szene.srv1, "eth0", szene.sw1, "Gi1"
    )
    # Wie nach einem Import: Kabel ohne Nummer.
    cable = await db.get(Cable, kabel["id"])
    cable.kabel_nr = None
    await db.commit()
    umbau = await _umbau(client, szene)
    await _bestaetige_alle(client, umbau["id"], szene)

    response = await client.post(f"{API}/{umbau['id']}/einfrieren", headers=HEADERS)

    assert response.status_code == 409, response.text
    assert f"Kabel #{kabel['id']}: Kabelnummer fehlt" in response.json()["detail"]


# === Port-Vergleich (Frage 4) ===============================================
async def test_anklemmen_mit_anderer_schreibweise_ist_soll(
    client: AsyncClient, db: AsyncSession
):
    _, umbau = await _eingefroren(client, db)
    await _bis_wiederaufbau(client, umbau)
    ende = next(e for e in umbau["enden"] if e["soll_port"] == "eth0")

    response = await _anklemmen(client, umbau["id"], ende["id"], ist_port="ETH0")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "angeklemmt"
    assert response.json()["ist_port"] is None


# === Soll mit Position und Länge (Frage 1) ==================================
async def test_einfrieren_kopiert_position_und_laenge(
    client: AsyncClient, db: AsyncSession
):
    szene = await _szene(db)
    szene.srv1.u_position = 12
    szene.srv1.u_hoehe = 2
    szene.sw1.u_position = 40
    szene.sw1.u_hoehe = 1
    await db.commit()
    response = await client.post(
        "/api/v1/cables/",
        json={
            "laenge_m": 2.5,
            "kabeltyp_id": szene.typen["rj45"].id,
            "von_device_id": szene.srv1.id,
            "von_port": "eth0",
            "nach_device_id": szene.sw1.id,
            "nach_port": "Gi1",
        },
    )
    assert response.status_code == 201, response.text
    umbau = await _umbau(client, szene)
    await _bestaetige_alle(client, umbau["id"], szene)

    detail = (
        await client.post(f"{API}/{umbau['id']}/einfrieren", headers=HEADERS)
    ).json()

    position = {e["soll_device_name"]: e["soll_position"] for e in detail["enden"]}
    assert position == {"umbau-srv1": "HE 12–13", "umbau-sw1": "HE 40"}
    assert {e["laenge_m"] for e in detail["enden"]} == {2.5}

    # Gerät wird danach umgesetzt: das Soll bleibt.
    srv1 = await db.get(Device, szene.srv1.id)
    srv1.u_position = 3
    await db.commit()
    nachher = (await client.get(f"{API}/{umbau['id']}")).json()
    assert {e["soll_position"] for e in nachher["enden"]} == {"HE 12–13", "HE 40"}


# === Unbekanntes Kabel nachtragen (Frage 7) ==================================
def _nachtrag(szene, **felder) -> dict:
    daten = {
        "kabeltyp_id": szene.typen["rj45"].id,
        "kabel_nr": "X-17",
        "farbe": "Gelb",
        "laenge_m": 3,
        "bemerkung": "lag hinter dem Kabelkanal",
        "a": {"device_id": szene.srv2.id, "port": "eth3"},
        "b": [{"device_id": szene.aussen.id, "port": "Gi9"}],
    }
    daten.update(felder)
    return daten


async def _nachtragen(client: AsyncClient, umbau_id: int, daten: dict):
    return await client.post(
        f"{API}/{umbau_id}/nachtraege", json=daten, headers=HEADERS
    )


async def test_nachtragen_legt_enden_ohne_kabel_an(
    client: AsyncClient, db: AsyncSession
):
    szene, umbau = await _eingefroren(client, db)
    kabel_vorher = (await db.execute(select(func.count()).select_from(Cable))).scalar()

    response = await _nachtragen(client, umbau["id"], _nachtrag(szene))

    assert response.status_code == 200, response.text
    detail = response.json()
    neu = [e for e in detail["enden"] if e["nachtrag_nr"] is not None]
    assert len(neu) == 2
    assert {e["nachtrag_nr"] for e in neu} == {1}
    assert all(e["cable_id"] is None for e in neu)
    assert all(e["status"] == "gesteckt" and e["sperrgrund"] is None for e in neu)
    a = next(e for e in neu if e["seite"] == "A")
    b = next(e for e in neu if e["seite"] == "B")
    assert (a["soll_device_name"], a["soll_port"]) == ("umbau-srv2", "eth3")
    assert (b["soll_device_name"], b["soll_port"]) == ("umbau-aussen", "Gi9")
    assert b["soll_rack_name"] == "Umbau-R2"
    assert a["kabel_nr"] == "X-17"
    assert a["kabeltyp_name"] == "Cat6A"
    assert a["farbe"] == "Gelb"
    assert a["laenge_m"] == 3
    assert a["gegenseite"] == ["umbau-aussen:Gi9"]
    assert detail["fortschritt"]["enden_gesamt"] == 4
    # Die Kabelliste bleibt unberührt.
    kabel_nachher = (await db.execute(select(func.count()).select_from(Cable))).scalar()
    assert kabel_nachher == kabel_vorher
    # Protokoll: je Ende ein Eintrag mit Bemerkung.
    ereignisse = (
        (
            await db.execute(
                select(UmbauEreignis).where(
                    UmbauEreignis.ende_id.in_([a["id"], b["id"]])
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(ereignisse) == 2
    assert all("nachgetragen" in (e.grund or "") for e in ereignisse)
    assert all("Kabelkanal" in (e.grund or "") for e in ereignisse)


async def test_nachgetragenes_kabel_muss_abgeklemmt_werden(
    client: AsyncClient, db: AsyncSession
):
    szene, umbau = await _eingefroren(client, db)
    detail = (await _nachtragen(client, umbau["id"], _nachtrag(szene))).json()
    for ende in detail["enden"]:
        if ende["nachtrag_nr"] is None:
            await _abklemmen(client, umbau["id"], ende["id"])

    gesperrt = await _status(client, umbau["id"], "umbau")
    assert gesperrt.status_code == 409, gesperrt.text

    for ende in detail["enden"]:
        if ende["nachtrag_nr"] is not None:
            antwort = await _abklemmen(client, umbau["id"], ende["id"])
            assert antwort.status_code == 200, antwort.text
    assert (await _status(client, umbau["id"], "umbau")).status_code == 200


async def test_nachtragen_ohne_nummer_vergibt_nummer(
    client: AsyncClient, db: AsyncSession
):
    szene, umbau = await _eingefroren(client, db)

    erste = await _nachtragen(client, umbau["id"], _nachtrag(szene, kabel_nr=None))
    zweite = await _nachtragen(
        client,
        umbau["id"],
        _nachtrag(
            szene,
            kabel_nr="",
            a={"device_id": szene.srv2.id, "port": "eth4"},
            b=[{"device_id": szene.aussen.id, "port": "Gi10"}],
        ),
    )

    assert erste.status_code == 200, erste.text
    assert zweite.status_code == 200, zweite.text
    nummern = {
        (e["nachtrag_nr"], e["kabel_nr"])
        for e in zweite.json()["enden"]
        if e["nachtrag_nr"] is not None
    }
    assert nummern == {(1, "NT-1"), (2, "NT-2")}


async def test_nachtragen_breakout_braucht_alle_b_enden(
    client: AsyncClient, db: AsyncSession
):
    szene, umbau = await _eingefroren(client, db)
    breakout = szene.typen["breakout"].id
    b_enden = [{"device_id": szene.srv2.id, "port": f"sfp{n}"} for n in range(1, 5)]

    zu_wenig = await _nachtragen(
        client, umbau["id"], _nachtrag(szene, kabeltyp_id=breakout, b=b_enden[:2])
    )
    passt = await _nachtragen(
        client, umbau["id"], _nachtrag(szene, kabeltyp_id=breakout, b=b_enden)
    )

    assert zu_wenig.status_code == 422, zu_wenig.text
    assert "4 B-Enden" in zu_wenig.json()["detail"]
    assert passt.status_code == 200, passt.text
    b = sorted(
        (
            e
            for e in passt.json()["enden"]
            if e["nachtrag_nr"] is not None and e["seite"] == "B"
        ),
        key=lambda e: e["ende_nr"],
    )
    assert [(e["ende_nr"], e["strand_number"]) for e in b] == [
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
    ]


async def test_nachtragen_lehnt_ungueltige_angaben_ab(
    client: AsyncClient, db: AsyncSession
):
    szene, umbau = await _eingefroren(client, db)
    umbau_id = umbau["id"]

    strom = await _nachtragen(
        client, umbau_id, _nachtrag(szene, kabeltyp_id=szene.typen["strom"].id)
    )
    unbekannter_typ = await _nachtragen(
        client, umbau_id, _nachtrag(szene, kabeltyp_id=999_999)
    )
    unbekanntes_geraet = await _nachtragen(
        client, umbau_id, _nachtrag(szene, a={"device_id": 999_999, "port": "x"})
    )
    doppelt_im_kabel = await _nachtragen(
        client,
        umbau_id,
        _nachtrag(szene, b=[{"device_id": szene.srv2.id, "port": "ETH3"}]),
    )
    # srv1:eth0 ist schon Soll des eingefrorenen Kabels.
    soll_belegt = await _nachtragen(
        client,
        umbau_id,
        _nachtrag(szene, a={"device_id": szene.srv1.id, "port": "Eth0"}),
    )
    nummer_belegt = await _nachtragen(
        client, umbau_id, _nachtrag(szene, kabel_nr=umbau["enden"][0]["kabel_nr"])
    )

    assert strom.status_code == 422, strom.text
    assert unbekannter_typ.status_code == 422, unbekannter_typ.text
    assert unbekanntes_geraet.status_code == 422, unbekanntes_geraet.text
    assert doppelt_im_kabel.status_code == 422, doppelt_im_kabel.text
    assert soll_belegt.status_code == 409, soll_belegt.text
    assert "umbau-srv1:Eth0" in soll_belegt.json()["detail"]
    assert nummer_belegt.status_code == 409, nummer_belegt.text
    anzahl = (
        await db.execute(
            select(func.count())
            .select_from(UmbauEnde)
            .where(UmbauEnde.nachtrag_nr.is_not(None))
        )
    ).scalar()
    assert anzahl == 0


async def test_nachtragen_ausserhalb_des_rueckbaus_ergibt_409(
    client: AsyncClient, db: AsyncSession
):
    szene = await _szene(db)
    await _verbinde(client, szene.typen["rj45"], szene.srv1, "eth0", szene.sw1, "Gi1")
    umbau = await _umbau(client, szene)

    in_erfassung = await _nachtragen(client, umbau["id"], _nachtrag(szene))

    assert in_erfassung.status_code == 409, in_erfassung.text


async def test_nachtrag_entfernen(client: AsyncClient, db: AsyncSession):
    szene, umbau = await _eingefroren(client, db)
    detail = (await _nachtragen(client, umbau["id"], _nachtrag(szene))).json()
    neu = [e for e in detail["enden"] if e["nachtrag_nr"] == 1]
    url = f"{API}/{umbau['id']}/nachtraege/1"

    # Abgeklemmt: erst zurücknehmen.
    await _abklemmen(client, umbau["id"], neu[0]["id"])
    gesperrt = await client.delete(url, headers=HEADERS)
    assert gesperrt.status_code == 409, gesperrt.text
    await _abklemmen(client, umbau["id"], neu[0]["id"], False)

    entfernt = await client.delete(url, headers=HEADERS)
    nochmal = await client.delete(url, headers=HEADERS)

    assert entfernt.status_code == 200, entfernt.text
    assert all(e["nachtrag_nr"] is None for e in entfernt.json()["enden"])
    assert entfernt.json()["fortschritt"]["enden_gesamt"] == 2
    assert nochmal.status_code == 200, nochmal.text
    protokoll = [
        e for e in entfernt.json()["ereignisse"] if e["nach_status"] == "entfernt"
    ]
    assert len(protokoll) == 1
    assert "X-17" in protokoll[0]["grund"]
