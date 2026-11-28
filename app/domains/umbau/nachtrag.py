"""Unbekannte Kabel im Rückbau nachtragen und wieder entfernen.

Findet man beim Abklemmen ein Kabel, das nicht in der Kabelliste steht, wird es hier
aufgenommen: je Stecker-Ende eine Zeile in `umbau_enden` mit cable_id NULL und einer
nachtrag_nr, die die Enden verbindet. Geschrieben wird nur in die Umbau-Tabellen, nie
in `cables`. Ins Kabelverzeichnis kommt so ein Kabel nach dem Umbau von Hand.
"""

from typing import Any, Sequence, cast

from fastapi import HTTPException
from sqlalchemy import CursorResult, delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.domains.cabling.models import Kabeltyp
from app.domains.umbau import regeln
from app.domains.umbau.models import UmbauEnde, UmbauEreignis
from app.domains.umbau.schemas import EndpunktEingabe, NachtragEingabe
from app.domains.umbau.services import Ort, UmbauService


class NachtragService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.umbauten = UmbauService(db)

    # --- Nachtragen ------------------------------------------------------------------
    async def nachtragen(
        self, umbau_id: int, eingabe: NachtragEingabe, username: str | None
    ) -> dict[str, Any]:
        umbau = await self.umbauten.get_umbau(umbau_id)
        sperre = regeln.nachtrag_sperrgrund(umbau.status)
        if sperre:
            raise HTTPException(status_code=409, detail=sperre)

        kabeltyp = await self._kabeltyp(eingabe)
        endpunkte = [eingabe.a, *eingabe.b]
        orte = await self._orte(endpunkte)
        _pruefe_doppelt(endpunkte, orte)
        enden = await self._enden(umbau_id)
        _pruefe_belegt(endpunkte, orte, enden)

        nachtrag_nr = max((e.nachtrag_nr or 0 for e in enden), default=0) + 1
        kabel_nr = eingabe.kabel_nr or f"NT-{nachtrag_nr}"
        if any(
            regeln.port_schluessel(e.kabel_nr) == regeln.port_schluessel(kabel_nr)
            for e in enden
        ):
            raise HTTPException(
                status_code=409,
                detail=f"Die Kabelnummer {kabel_nr} gibt es in diesem Umbau schon.",
            )

        breakout = kabeltyp.enden_b > 1
        gemeinsam = {
            "umbau_id": umbau.id,
            "cable_id": None,
            "nachtrag_nr": nachtrag_nr,
            "kabel_nr": kabel_nr,
            "kabeltyp_name": kabeltyp.name,
            "kategorie": kabeltyp.kategorie,
            "farbe": eingabe.farbe or kabeltyp.standard_farbe,
            "laenge_m": eingabe.laenge_m,
            "status": regeln.GESTECKT,
        }
        seiten = [("A", 1, None, eingabe.a)] + [
            ("B", nr, nr if breakout else None, punkt)
            for nr, punkt in enumerate(eingabe.b, start=1)
        ]
        neue = []
        for seite, ende_nr, strand_number, punkt in seiten:
            ort = orte[punkt.device_id]
            neue.append(
                UmbauEnde(
                    **gemeinsam,
                    seite=seite,
                    ende_nr=ende_nr,
                    strand_number=strand_number,
                    soll_device_id=punkt.device_id,
                    soll_device_name=ort.name,
                    soll_rack_name=ort.rack_name,
                    soll_position=ort.position,
                    soll_port=punkt.port,
                )
            )
        self.db.add_all(neue)
        await self.db.flush()

        grund = "Kabel nachgetragen" + (
            f": {eingabe.bemerkung}" if eingabe.bemerkung else ""
        )
        for ende in neue:
            self.db.add(
                UmbauEreignis(
                    umbau_id=umbau.id,
                    ende_id=ende.id,
                    von_status=None,
                    nach_status=regeln.GESTECKT,
                    grund=grund,
                    benutzer=username,
                )
            )
        await self.db.commit()
        return await self.umbauten.detail(umbau.id)

    async def _kabeltyp(self, eingabe: NachtragEingabe) -> Kabeltyp:
        kabeltyp = await self.db.get(Kabeltyp, eingabe.kabeltyp_id)
        if kabeltyp is None:
            raise HTTPException(
                status_code=422,
                detail=f"Kabeltyp {eingabe.kabeltyp_id} existiert nicht",
            )
        if kabeltyp.kategorie == "strom":
            raise HTTPException(
                status_code=422, detail="Stromkabel gehören nicht zum Umbau."
            )
        if kabeltyp.enden_a != 1:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Kabeltyp „{kabeltyp.name}“ mit {kabeltyp.enden_a} A-Enden wird im "
                    "Umbau nicht unterstützt."
                ),
            )
        if len(eingabe.b) != kabeltyp.enden_b:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Kabeltyp „{kabeltyp.name}“ hat {kabeltyp.enden_b} B-Enden, "
                    f"angegeben sind {len(eingabe.b)}."
                ),
            )
        return kabeltyp

    async def _orte(self, endpunkte: Sequence[EndpunktEingabe]) -> dict[int, Ort]:
        ids = {punkt.device_id for punkt in endpunkte}
        orte = await self.umbauten.geraete_orte(ids)
        fehlend = sorted(ids - set(orte))
        if fehlend:
            raise HTTPException(
                status_code=422,
                detail=f"Gerät(e) existieren nicht: {', '.join(map(str, fehlend))}",
            )
        return orte

    async def _enden(
        self, umbau_id: int, nachtrag_nr: int | None = None
    ) -> Sequence[UmbauEnde]:
        query = select(UmbauEnde).where(UmbauEnde.umbau_id == umbau_id)
        if nachtrag_nr is not None:
            query = query.where(UmbauEnde.nachtrag_nr == nachtrag_nr)
        result = await self.db.execute(query.execution_options(populate_existing=True))
        return result.scalars().all()

    # --- Entfernen (Tippfehler korrigieren) --------------------------------------------
    async def entfernen(
        self, umbau_id: int, nachtrag_nr: int, username: str | None
    ) -> dict[str, Any]:
        umbau = await self.umbauten.get_umbau(umbau_id)
        enden = await self._enden(umbau_id, nachtrag_nr)
        if not enden:
            return await self.umbauten.detail(umbau.id)  # Ziel schon erreicht
        sperre = regeln.nachtrag_entfernen_sperrgrund(
            umbau.status, [ende.status for ende in enden]
        )
        if sperre:
            raise HTTPException(status_code=409, detail=sperre)

        # Ein Statement: löscht nur, wenn kein Ende des Nachtrags inzwischen abgeklemmt ist.
        anderes = aliased(UmbauEnde)
        result = await self.db.execute(
            delete(UmbauEnde)
            .where(
                UmbauEnde.umbau_id == umbau_id,
                UmbauEnde.nachtrag_nr == nachtrag_nr,
                ~exists().where(
                    anderes.umbau_id == umbau_id,
                    anderes.nachtrag_nr == nachtrag_nr,
                    anderes.status != regeln.GESTECKT,
                ),
            )
            .execution_options(synchronize_session=False)
        )
        if cast(CursorResult[Any], result).rowcount == 0:
            # Jemand war schneller: neu lesen und entscheiden, ohne Ereignis.
            verblieben = await self._enden(umbau_id, nachtrag_nr)
            if not verblieben:
                return await self.umbauten.detail(umbau.id)
            raise HTTPException(
                status_code=409,
                detail=regeln.nachtrag_entfernen_sperrgrund(
                    umbau.status, [ende.status for ende in verblieben]
                )
                or "Der Nachtrag wurde inzwischen geändert.",
            )

        self.db.add(
            UmbauEreignis(
                umbau_id=umbau.id,
                von_status=regeln.GESTECKT,
                nach_status="entfernt",
                grund=(
                    f"Nachgetragenes Kabel {enden[0].kabel_nr} entfernt "
                    f"({len(enden)} Enden)"
                ),
                benutzer=username,
            )
        )
        await self.db.commit()
        return await self.umbauten.detail(umbau.id)


def _anzeige(ort: Ort, port: str) -> str:
    return f"{ort.name}:{port}"


def _pruefe_doppelt(endpunkte: Sequence[EndpunktEingabe], orte: dict[int, Ort]) -> None:
    gesehen: set[tuple[int, str]] = set()
    for punkt in endpunkte:
        schluessel = (punkt.device_id, regeln.port_schluessel(punkt.port))
        if schluessel in gesehen:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{_anzeige(orte[punkt.device_id], punkt.port)} ist in diesem Kabel "
                    "doppelt angegeben."
                ),
            )
        gesehen.add(schluessel)


def _pruefe_belegt(
    endpunkte: Sequence[EndpunktEingabe],
    orte: dict[int, Ort],
    enden: Sequence[UmbauEnde],
) -> None:
    """Ein Port, der schon Soll eines Endes in diesem Umbau ist, ist belegt."""
    belegt = {
        (ende.soll_device_id, regeln.port_schluessel(ende.soll_port)): ende.kabel_nr
        for ende in enden
        if ende.soll_device_id is not None
    }
    for punkt in endpunkte:
        schluessel = (punkt.device_id, regeln.port_schluessel(punkt.port))
        if schluessel in belegt:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{_anzeige(orte[punkt.device_id], punkt.port)} ist im Soll schon "
                    f"belegt (Kabel {belegt[schluessel] or 'ohne Nummer'})."
                ),
            )
