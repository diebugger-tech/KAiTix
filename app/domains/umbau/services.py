"""Umbau anlegen, lesen, Geräte bestätigen, einfrieren und Status wechseln.

Kabel werden hier nur gelesen. Angelegt und geändert werden sie in der Erfassung über
die vorhandenen /cables-Endpunkte. Ab dem Einfrieren arbeitet der Umbau ausschließlich
auf seinen eigenen Tabellen.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Any, Sequence

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.cabling.models import Cable
from app.domains.hardware.models import Device, Rack
from app.domains.umbau import regeln
from app.domains.umbau.models import (
    Umbau,
    UmbauEnde,
    UmbauEreignis,
    UmbauGeraetepruefung,
    UmbauRack,
    jetzt,
)
from app.domains.umbau.schemas import UmbauCreate


@dataclass(frozen=True)
class Umfang:
    """Was in der Erfassung zum Umbau gehört."""

    geraete: Sequence[Device]
    kabel: Sequence[regeln.KabelSicht]
    bestaetigungen: dict[int, UmbauGeraetepruefung]
    sperren: Sequence[str]


def kabel_sicht(cable: Cable) -> regeln.KabelSicht:
    """Kabel aus der Datenbank in die Sicht der Regeln übersetzen."""
    kabeltyp = cable.kabeltyp
    return regeln.KabelSicht(
        id=cable.id,
        kabel_nr=cable.kabel_nr,
        typ=cable.typ,
        kategorie=kabeltyp.kategorie if kabeltyp else None,
        kabeltyp_name=kabeltyp.name if kabeltyp else None,
        enden_a=kabeltyp.enden_a if kabeltyp else 1,
        enden_b=kabeltyp.enden_b if kabeltyp else 1,
        farbe=cable.farbe,
        von=(cable.von_device_id, cable.von_port),
        nach=(cable.nach_device_id, cable.nach_port),
        straenge=tuple(
            regeln.StrangSicht(
                strand_number=strang.strand_number,
                device_id=strang.nach_device_id,
                port=strang.nach_port,
                farbe=strang.farbe,
            )
            for strang in cable.cable_strands
        ),
    )


def zaehle_enden(status_liste: Sequence[str]) -> dict[str, int]:
    """Fortschrittszahlen aus den Status der Enden."""
    je_status = Counter(status_liste)
    abweichend = je_status.get(regeln.ANGEKLEMMT_ABWEICHEND, 0)
    return {
        "enden_gesamt": len(status_liste),
        "gesteckt": je_status.get(regeln.GESTECKT, 0),
        "abgeklemmt": je_status.get(regeln.ABGEKLEMMT, 0),
        "angeklemmt": je_status.get(regeln.ANGEKLEMMT, 0) + abweichend,
        "abweichend": abweichend,
    }


class UmbauService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Laden ---------------------------------------------------------------
    async def get_umbau(self, umbau_id: int) -> Umbau:
        # populate_existing: immer den Stand der Datenbank, nie ein Objekt aus der Session.
        result = await self.db.execute(
            select(Umbau)
            .where(Umbau.id == umbau_id)
            .options(selectinload(Umbau.racks))
            .execution_options(populate_existing=True)
        )
        umbau = result.scalar_one_or_none()
        if umbau is None:
            raise HTTPException(status_code=404, detail="Umbau nicht gefunden")
        return umbau

    async def _racks(self, umbau: Umbau) -> list[dict[str, Any]]:
        rack_ids = [eintrag.rack_id for eintrag in umbau.racks]
        if not rack_ids:
            return []
        result = await self.db.execute(
            select(Rack.id, Rack.name).where(Rack.id.in_(rack_ids)).order_by(Rack.name)
        )
        return [{"id": rack_id, "name": name} for rack_id, name in result.all()]

    async def _rack_namen(self) -> dict[int, str]:
        result = await self.db.execute(select(Rack.id, Rack.name))
        return {rack_id: name for rack_id, name in result.all()}

    async def _alle_kabel(self) -> list[regeln.KabelSicht]:
        result = await self.db.execute(
            select(Cable)
            .options(selectinload(Cable.cable_strands), selectinload(Cable.kabeltyp))
            .order_by(Cable.id)
            .execution_options(populate_existing=True)
        )
        return [kabel_sicht(cable) for cable in result.scalars()]

    async def _umfang(self, umbau: Umbau) -> Umfang:
        rack_ids = [eintrag.rack_id for eintrag in umbau.racks]
        geraete: Sequence[Device] = []
        if rack_ids:
            result = await self.db.execute(
                select(Device)
                .where(Device.rack_id.in_(rack_ids))
                .order_by(Device.hostname)
            )
            geraete = result.scalars().all()
        geraete_ids = {geraet.id for geraet in geraete}
        kabel = [
            sicht
            for sicht in await self._alle_kabel()
            if regeln.im_umfang(sicht, geraete_ids)
        ]
        result = await self.db.execute(
            select(UmbauGeraetepruefung)
            .where(UmbauGeraetepruefung.umbau_id == umbau.id)
            .execution_options(populate_existing=True)
        )
        bestaetigungen = {
            pruefung.device_id: pruefung
            for pruefung in result.scalars()
            if pruefung.device_id is not None
        }
        sperren = regeln.einfrier_sperren(
            kabel,
            [(geraet.id, geraet.hostname) for geraet in geraete],
            set(bestaetigungen),
        )
        return Umfang(
            geraete=geraete, kabel=kabel, bestaetigungen=bestaetigungen, sperren=sperren
        )

    async def _enden(self, umbau_id: int) -> Sequence[UmbauEnde]:
        result = await self.db.execute(
            select(UmbauEnde)
            .where(UmbauEnde.umbau_id == umbau_id)
            .order_by(
                UmbauEnde.soll_rack_name,
                UmbauEnde.soll_device_name,
                UmbauEnde.soll_port,
                UmbauEnde.id,
            )
            .execution_options(populate_existing=True)
        )
        return result.scalars().all()

    async def _enden_je_status(self, umbau_id: int) -> dict[str, int]:
        result = await self.db.execute(
            select(UmbauEnde.status, func.count())
            .where(UmbauEnde.umbau_id == umbau_id)
            .group_by(UmbauEnde.status)
        )
        return {status: int(anzahl) for status, anzahl in result.all()}

    # --- Anlegen und Listen -----------------------------------------------------
    async def create_umbau(
        self, umbau_in: UmbauCreate, username: str | None
    ) -> dict[str, Any]:
        rack_ids = sorted(set(umbau_in.rack_ids))
        result = await self.db.execute(select(Rack.id).where(Rack.id.in_(rack_ids)))
        vorhanden = set(result.scalars())
        fehlend = [rack_id for rack_id in rack_ids if rack_id not in vorhanden]
        if fehlend:
            raise HTTPException(
                status_code=422,
                detail=f"Rack(s) existieren nicht: {', '.join(map(str, fehlend))}",
            )
        umbau = Umbau(
            name=umbau_in.name,
            beschreibung=umbau_in.beschreibung,
            status=regeln.ERFASSUNG,
            erstellt_von=username,
            racks=[UmbauRack(rack_id=rack_id) for rack_id in rack_ids],
        )
        self.db.add(umbau)
        await self.db.flush()
        self.db.add(
            UmbauEreignis(
                umbau_id=umbau.id,
                von_status=None,
                nach_status=regeln.ERFASSUNG,
                benutzer=username,
            )
        )
        await self.db.commit()
        return await self.detail(umbau.id)

    async def list_umbauten(self) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(Umbau)
            .options(selectinload(Umbau.racks))
            .order_by(Umbau.id.desc())
            .execution_options(populate_existing=True)
        )
        liste: list[dict[str, Any]] = []
        for umbau in result.scalars().all():
            eintrag = self._kopf(umbau)
            eintrag["racks"] = await self._racks(umbau)
            eintrag["fortschritt"] = zaehle_enden(
                [ende.status for ende in await self._enden(umbau.id)]
            )
            if umbau.status == regeln.ERFASSUNG:
                umfang = await self._umfang(umbau)
                eintrag["geraete_gesamt"] = len(umfang.geraete)
                eintrag["geraete_bestaetigt"] = sum(
                    1 for geraet in umfang.geraete if geraet.id in umfang.bestaetigungen
                )
            liste.append(eintrag)
        return liste

    # --- Detail ---------------------------------------------------------------
    async def detail(self, umbau_id: int) -> dict[str, Any]:
        umbau = await self.get_umbau(umbau_id)
        enden = await self._enden(umbau.id)
        zahlen = zaehle_enden([ende.status for ende in enden])

        geraete: list[dict[str, Any]] = []
        sperren: Sequence[str] = []
        if umbau.status == regeln.ERFASSUNG:
            umfang = await self._umfang(umbau)
            sperren = umfang.sperren
            geraete = self._geraete_erfassung(umfang, await self._rack_namen())

        je_status = Counter(ende.status for ende in enden)
        ereignisse = await self.db.execute(
            select(UmbauEreignis)
            .where(UmbauEreignis.umbau_id == umbau.id)
            .order_by(UmbauEreignis.id.desc())
        )
        antwort = self._kopf(umbau)
        antwort.update(
            racks=await self._racks(umbau),
            geraete=geraete,
            einfrier_sperren=list(sperren),
            enden=self._enden_out(enden, umbau.status),
            fortschritt=zahlen,
            fortschritt_racks=self._fortschritt_racks(enden),
            naechste_status=[
                {
                    "ziel": ziel,
                    "sperrgrund": regeln.umbau_uebergang_sperrgrund(
                        umbau.status, ziel, je_status, sperren
                    ),
                }
                for ziel in regeln.naechste_ziele(umbau.status)
            ],
            ereignisse=ereignisse.scalars().all(),
        )
        return antwort

    @staticmethod
    def _kopf(umbau: Umbau) -> dict[str, Any]:
        return {
            "id": umbau.id,
            "name": umbau.name,
            "beschreibung": umbau.beschreibung,
            "status": umbau.status,
            "erstellt_am": umbau.erstellt_am,
            "erstellt_von": umbau.erstellt_von,
            "eingefroren_am": umbau.eingefroren_am,
            "eingefroren_von": umbau.eingefroren_von,
            "abgeschlossen_am": umbau.abgeschlossen_am,
            "abgeschlossen_von": umbau.abgeschlossen_von,
        }

    @staticmethod
    def _geraete_erfassung(
        umfang: Umfang, rack_namen: dict[int, str]
    ) -> list[dict[str, Any]]:
        """Erfassungsfortschritt je Gerät: Kabel am Gerät, davon unvollständig, bestätigt."""
        kabel_je_geraet: Counter[int] = Counter()
        offen_je_geraet: Counter[int] = Counter()
        for kabel in umfang.kabel:
            unvollstaendig = bool(regeln.unvollstaendig(kabel))
            for device_id in regeln.geraete_eines_kabels(kabel):
                kabel_je_geraet[device_id] += 1
                if unvollstaendig:
                    offen_je_geraet[device_id] += 1
        ergebnis = []
        for geraet in umfang.geraete:
            pruefung = umfang.bestaetigungen.get(geraet.id)
            ergebnis.append(
                {
                    "device_id": geraet.id,
                    "hostname": geraet.hostname,
                    "typ": geraet.typ,
                    "rack_id": geraet.rack_id,
                    "rack_name": rack_namen.get(geraet.rack_id)
                    if geraet.rack_id
                    else None,
                    "kabel_gesamt": kabel_je_geraet[geraet.id],
                    "kabel_unvollstaendig": offen_je_geraet[geraet.id],
                    "bestaetigt": pruefung is not None,
                    "bestaetigt_am": pruefung.bestaetigt_am if pruefung else None,
                    "bestaetigt_von": pruefung.bestaetigt_von if pruefung else None,
                }
            )
        return ergebnis

    @staticmethod
    def _enden_out(
        enden: Sequence[UmbauEnde], umbau_status: str
    ) -> list[dict[str, Any]]:
        """Enden mit Gegenseite und Sperrgrund. Beides ist abgeleitet, nicht gespeichert."""
        # Enden desselben Kabels finden sich über cable_id; ist das Kabel inzwischen
        # gelöscht (cable_id NULL), hilft die Kabelnummer aus der Textkopie.
        gruppen: dict[str, list[UmbauEnde]] = {}
        for ende in enden:
            gruppen.setdefault(_kabel_schluessel(ende), []).append(ende)
        ergebnis = []
        for ende in enden:
            daten = {
                spalte.name: getattr(ende, spalte.name)
                for spalte in UmbauEnde.__table__.columns
            }
            daten["gegenseite"] = [
                f"{anderes.soll_device_name}:{anderes.soll_port}"
                for anderes in gruppen[_kabel_schluessel(ende)]
                if anderes.seite != ende.seite
            ]
            daten["sperrgrund"] = regeln.sperrgrund(ende.status, umbau_status)
            ergebnis.append(daten)
        return ergebnis

    @staticmethod
    def _fortschritt_racks(enden: Sequence[UmbauEnde]) -> list[dict[str, Any]]:
        racks: dict[str, dict[str, list[str]]] = {}
        for ende in enden:
            rack = ende.soll_rack_name or "Ohne Rack"
            racks.setdefault(rack, {}).setdefault(ende.soll_device_name, []).append(
                ende.status
            )
        return [
            {
                "rack_name": rack,
                "fortschritt": zaehle_enden(
                    [status for liste in geraete.values() for status in liste]
                ),
                "geraete": [
                    {"device_name": name, "fortschritt": zaehle_enden(liste)}
                    for name, liste in sorted(geraete.items())
                ],
            }
            for rack, geraete in sorted(racks.items())
        ]

    # --- Erfassung: Gerät bestätigen -------------------------------------------
    async def bestaetigen(
        self, umbau_id: int, device_id: int, bestaetigt: bool, username: str | None
    ) -> dict[str, Any]:
        umbau = await self.get_umbau(umbau_id)
        if umbau.status != regeln.ERFASSUNG:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Geräte lassen sich nur in der Erfassung bestätigen. Der Umbau ist "
                    f"im Status „{regeln.UMBAU_STATUS_LABEL[umbau.status]}“."
                ),
            )
        geraet = await self.db.get(Device, device_id)
        if geraet is None:
            raise HTTPException(status_code=404, detail="Gerät nicht gefunden")
        if geraet.rack_id not in {eintrag.rack_id for eintrag in umbau.racks}:
            raise HTTPException(
                status_code=409,
                detail=f"Gerät '{geraet.hostname}' liegt nicht im Umfang dieses Umbaus",
            )

        result = await self.db.execute(
            select(UmbauGeraetepruefung)
            .where(
                UmbauGeraetepruefung.umbau_id == umbau.id,
                UmbauGeraetepruefung.device_id == device_id,
            )
            .execution_options(populate_existing=True)
        )
        pruefung = result.scalar_one_or_none()
        # Idempotent: nur schreiben, wenn sich etwas ändert.
        if bestaetigt and pruefung is None:
            self.db.add(
                UmbauGeraetepruefung(
                    umbau_id=umbau.id,
                    device_id=device_id,
                    device_name=geraet.hostname,
                    bestaetigt_von=username,
                )
            )
            await self.db.commit()
        elif not bestaetigt and pruefung is not None:
            await self.db.delete(pruefung)
            await self.db.commit()

        umfang = await self._umfang(umbau)
        geraete = self._geraete_erfassung(umfang, await self._rack_namen())
        return next(eintrag for eintrag in geraete if eintrag["device_id"] == device_id)

    # --- Einfrieren -------------------------------------------------------------
    async def einfrieren(self, umbau_id: int, username: str | None) -> dict[str, Any]:
        umbau = await self.get_umbau(umbau_id)
        if umbau.status == regeln.RUECKBAU:
            return await self.detail(umbau.id)  # Ziel schon erreicht

        umfang = await self._umfang(umbau)
        grund = regeln.umbau_uebergang_sperrgrund(
            umbau.status, regeln.RUECKBAU, {}, umfang.sperren
        )
        if grund:
            raise HTTPException(status_code=409, detail=grund)

        result = await self.db.execute(
            update(Umbau)
            .where(Umbau.id == umbau.id, Umbau.status == regeln.ERFASSUNG)
            .values(
                status=regeln.RUECKBAU, eingefroren_am=jetzt(), eingefroren_von=username
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            return await self._nach_verlorenem_wechsel(umbau, regeln.RUECKBAU)

        # Soll-Stand als Textkopie festhalten: je physischem Ende eine Zeile.
        geraete = await self._geraete_namen()
        rack_namen = await self._rack_namen()
        for kabel in umfang.kabel:
            for ende in regeln.enden_fuer_kabel(kabel):
                name, rack_id = geraete[ende.device_id]  # type: ignore[index]
                self.db.add(
                    UmbauEnde(
                        umbau_id=umbau.id,
                        cable_id=kabel.id,
                        strand_number=ende.strand_number,
                        seite=ende.seite,
                        ende_nr=ende.ende_nr,
                        soll_device_id=ende.device_id,
                        soll_device_name=name,
                        soll_rack_name=rack_namen.get(rack_id) if rack_id else None,
                        soll_port=ende.port,
                        kabel_nr=kabel.kabel_nr,
                        kabeltyp_name=kabel.kabeltyp_name,
                        kategorie=kabel.kategorie,
                        farbe=ende.farbe,
                        status=regeln.GESTECKT,
                    )
                )
        self.db.add(
            UmbauEreignis(
                umbau_id=umbau.id,
                von_status=regeln.ERFASSUNG,
                nach_status=regeln.RUECKBAU,
                benutzer=username,
            )
        )
        await self.db.commit()
        return await self.detail(umbau.id)

    async def _geraete_namen(self) -> dict[int, tuple[str, int | None]]:
        result = await self.db.execute(
            select(Device.id, Device.hostname, Device.rack_id)
        )
        return {device_id: (name, rack_id) for device_id, name, rack_id in result.all()}

    # --- Statuswechsel ------------------------------------------------------------
    async def status_wechsel(
        self, umbau_id: int, ziel: str, username: str | None
    ) -> dict[str, Any]:
        umbau = await self.get_umbau(umbau_id)
        if umbau.status == ziel:
            return await self.detail(umbau.id)  # Ziel schon erreicht
        if umbau.status == regeln.ERFASSUNG and ziel == regeln.RUECKBAU:
            return await self.einfrieren(umbau_id, username)

        erwartet = umbau.status
        grund = regeln.umbau_uebergang_sperrgrund(
            erwartet, ziel, await self._enden_je_status(umbau.id)
        )
        if grund:
            raise HTTPException(status_code=409, detail=grund)

        werte: dict[str, Any] = {"status": ziel}
        if ziel == regeln.ABGESCHLOSSEN:
            werte.update(abgeschlossen_am=jetzt(), abgeschlossen_von=username)
        result = await self.db.execute(
            update(Umbau)
            .where(Umbau.id == umbau.id, Umbau.status == erwartet)
            .values(**werte)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            return await self._nach_verlorenem_wechsel(umbau, ziel)

        self.db.add(
            UmbauEreignis(
                umbau_id=umbau.id,
                von_status=erwartet,
                nach_status=ziel,
                benutzer=username,
            )
        )
        await self.db.commit()
        return await self.detail(umbau.id)

    async def _nach_verlorenem_wechsel(self, umbau: Umbau, ziel: str) -> dict[str, Any]:
        """rowcount 0: jemand war schneller. Neu lesen und entscheiden, ohne Ereignis."""
        await self.db.refresh(umbau, attribute_names=["status"])
        if umbau.status == ziel:
            return await self.detail(umbau.id)
        grund = regeln.umbau_uebergang_sperrgrund(
            umbau.status, ziel, await self._enden_je_status(umbau.id)
        )
        raise HTTPException(
            status_code=409,
            detail=grund
            or (
                "Der Umbau wurde inzwischen geändert und ist jetzt im Status "
                f"„{regeln.UMBAU_STATUS_LABEL.get(umbau.status, umbau.status)}“."
            ),
        )


def _kabel_schluessel(ende: UmbauEnde) -> str:
    if ende.cable_id is not None:
        return f"id:{ende.cable_id}"
    return f"nr:{ende.kabel_nr}" if ende.kabel_nr else f"ende:{ende.id}"
