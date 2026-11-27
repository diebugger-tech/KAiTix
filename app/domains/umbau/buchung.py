"""Buchungen an einzelnen Enden: abklemmen, anklemmen und deren Rücknahme.

Gleichzeitigkeit ohne Zeilensperren (SQLite): bedingtes UPDATE mit dem erwarteten
Status. Trifft es keine Zeile, war jemand schneller: neu lesen, dann entweder
„Ziel schon erreicht“ (ohne Änderung, ohne Ereignis) oder 409 mit Sperrgrund.
Das Ereignis entsteht nur bei rowcount 1, in derselben Transaktion.
"""

from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.hardware.models import Device
from app.domains.umbau import regeln
from app.domains.umbau.models import Umbau, UmbauEnde, UmbauEreignis, jetzt
from app.domains.umbau.schemas import AnklemmenEingabe

# Felder, die beim Zurücknehmen des Anklemmens bzw. beim Anklemmen nach Soll leer sind.
KEIN_IST: dict[str, Any] = {
    "ist_device_id": None,
    "ist_device_name": None,
    "ist_port": None,
    "abweichung_grund": None,
}


class EndenBuchung:
    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Abklemmen -------------------------------------------------------------
    async def abklemmen(
        self, umbau_id: int, ende_id: int, abgeklemmt: bool, username: str | None
    ) -> dict[str, Any]:
        aktion = regeln.ABKLEMMEN if abgeklemmt else regeln.ABKLEMMEN_ZURUECK
        umbau, ende = await self._lade(umbau_id, ende_id, aktion)
        if abgeklemmt:
            werte: dict[str, Any] = {
                "abgeklemmt_am": jetzt(),
                "abgeklemmt_von": username,
            }
        else:
            werte = {"abgeklemmt_am": None, "abgeklemmt_von": None}
        return await self._buchen(umbau, ende, aktion, werte, username)

    # --- Anklemmen -------------------------------------------------------------
    async def anklemmen(
        self,
        umbau_id: int,
        ende_id: int,
        eingabe: AnklemmenEingabe,
        username: str | None,
    ) -> dict[str, Any]:
        if not eingabe.angeklemmt:
            umbau, ende = await self._lade(umbau_id, ende_id, regeln.ANKLEMMEN_ZURUECK)
            werte: dict[str, Any] = {
                "angeklemmt_am": None,
                "angeklemmt_von": None,
                **KEIN_IST,
            }
            return await self._buchen(
                umbau, ende, regeln.ANKLEMMEN_ZURUECK, werte, username
            )

        umbau, ende = await self._lade(umbau_id, ende_id, regeln.ANKLEMMEN)
        soll = (ende.soll_device_id, ende.soll_port)
        if not regeln.ist_abweichung(soll, eingabe.ist_device_id, eingabe.ist_port):
            werte = {"angeklemmt_am": jetzt(), "angeklemmt_von": username, **KEIN_IST}
            return await self._buchen(umbau, ende, regeln.ANKLEMMEN, werte, username)

        # Anderer Port als Soll: nur mit Grund.
        if not eingabe.grund:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Anklemmen an einem anderen Port als im Soll braucht einen Grund."
                ),
            )
        ist_device_id = (
            eingabe.ist_device_id
            if eingabe.ist_device_id is not None
            else ende.soll_device_id
        )
        ist = {
            "ist_device_id": ist_device_id,
            "ist_device_name": await self._device_name(ist_device_id, ende),
            "ist_port": eingabe.ist_port or ende.soll_port,
            "abweichung_grund": eingabe.grund,
        }
        if ende.status == regeln.ANGEKLEMMT_ABWEICHEND and (
            ende.ist_device_id,
            ende.ist_port,
        ) != (ist["ist_device_id"], ist["ist_port"]):
            # Schon abweichend angeklemmt, aber woanders: erst zurücknehmen.
            raise HTTPException(
                status_code=409,
                detail=regeln.aktion_sperrgrund(
                    regeln.ANKLEMMEN, ende.status, umbau.status
                ),
            )
        werte = {"angeklemmt_am": jetzt(), "angeklemmt_von": username, **ist}
        return await self._buchen(
            umbau,
            ende,
            regeln.ANKLEMMEN_ABWEICHEND,
            werte,
            username,
            grund=eingabe.grund,
        )

    # --- Gemeinsamer Ablauf ------------------------------------------------------
    async def _lade(
        self, umbau_id: int, ende_id: int, aktion: str
    ) -> tuple[Umbau, UmbauEnde]:
        umbau = await self.db.get(Umbau, umbau_id, populate_existing=True)
        if umbau is None:
            raise HTTPException(status_code=404, detail="Umbau nicht gefunden")
        # Zuerst die Phase: Abklemmen gibt es nur im Rückbau, Anklemmen nur im
        # Wiederaufbau, unabhängig vom Status des einzelnen Endes.
        if umbau.status != regeln.AKTION_PHASE[aktion]:
            raise HTTPException(
                status_code=409,
                detail=regeln.aktion_sperrgrund(aktion, regeln.GESTECKT, umbau.status),
            )
        result = await self.db.execute(
            select(UmbauEnde).where(
                UmbauEnde.id == ende_id, UmbauEnde.umbau_id == umbau_id
            )
        )
        ende = result.scalar_one_or_none()
        if ende is None:
            raise HTTPException(status_code=404, detail="Ende nicht gefunden")
        return umbau, ende

    async def _buchen(
        self,
        umbau: Umbau,
        ende: UmbauEnde,
        aktion: str,
        werte: dict[str, Any],
        username: str | None,
        grund: str | None = None,
    ) -> dict[str, Any]:
        if regeln.ziel_schon_erreicht(aktion, ende.status):
            return self._out(ende, umbau.status)
        sperre = regeln.aktion_sperrgrund(aktion, ende.status, umbau.status)
        if sperre:
            raise HTTPException(status_code=409, detail=sperre)

        erwartet = ende.status
        ziel = regeln.ziel_status(aktion, erwartet)
        result = await self.db.execute(
            update(UmbauEnde)
            .where(UmbauEnde.id == ende.id, UmbauEnde.status == erwartet)
            .values(status=ziel, **werte)
            .execution_options(synchronize_session=False)
        )
        if cast(CursorResult[Any], result).rowcount != 1:
            # Jemand war schneller: neu lesen und entscheiden. Kein Ereignis.
            await self.db.refresh(ende)
            if regeln.ziel_schon_erreicht(aktion, ende.status):
                return self._out(ende, umbau.status)
            raise HTTPException(
                status_code=409,
                detail=regeln.aktion_sperrgrund(aktion, ende.status, umbau.status)
                or (
                    "Das Ende wurde inzwischen geändert und ist jetzt im Status "
                    f"„{ende.status}“."
                ),
            )

        self.db.add(
            UmbauEreignis(
                umbau_id=umbau.id,
                ende_id=ende.id,
                von_status=erwartet,
                nach_status=ziel,
                grund=grund,
                benutzer=username,
            )
        )
        await self.db.commit()
        await self.db.refresh(ende)
        return self._out(ende, umbau.status)

    async def _device_name(self, device_id: int | None, ende: UmbauEnde) -> str:
        if device_id is None or device_id == ende.soll_device_id:
            return ende.soll_device_name
        result = await self.db.execute(
            select(Device.hostname).where(Device.id == device_id)
        )
        name = result.scalar_one_or_none()
        if name is None:
            raise HTTPException(
                status_code=422, detail=f"Gerät {device_id} existiert nicht"
            )
        return name

    @staticmethod
    def _out(ende: UmbauEnde, umbau_status: str) -> dict[str, Any]:
        daten = {
            spalte.name: getattr(ende, spalte.name)
            for spalte in UmbauEnde.__table__.columns
        }
        # Die Gegenseite liefert nur GET /umbau/{id}, dort stehen alle Enden zusammen.
        daten["gegenseite"] = []
        daten["sperrgrund"] = regeln.sperrgrund(ende.status, umbau_status)
        return daten
