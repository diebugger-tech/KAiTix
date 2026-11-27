from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_username
from app.core.database import get_db
from app.domains.umbau.buchung import EndenBuchung
from app.domains.umbau.nachtrag import NachtragService
from app.domains.umbau.schemas import (
    AnklemmenEingabe,
    EndeOut,
    GeraetErfassung,
    NachtragEingabe,
    StatusWechsel,
    UmbauCreate,
    UmbauDetail,
    UmbauListe,
)
from app.domains.umbau.services import UmbauService

router = APIRouter()


@router.post("/", response_model=UmbauDetail, status_code=status.HTTP_201_CREATED)
async def create_umbau(
    umbau_in: UmbauCreate,
    db: AsyncSession = Depends(get_db),
    username: str | None = Depends(get_username),
):
    """Legt einen Umbau im Status „erfassung“ an. Der Umfang sind die gewählten Racks."""
    return await UmbauService(db).create_umbau(umbau_in, username)


@router.get("/", response_model=List[UmbauListe])
async def list_umbauten(db: AsyncSession = Depends(get_db)):
    return await UmbauService(db).list_umbauten()


@router.get("/{umbau_id}", response_model=UmbauDetail)
async def get_umbau(umbau_id: int, db: AsyncSession = Depends(get_db)):
    """Umbau mit Erfassungsfortschritt je Gerät, Enden, Fortschritt und Sperrgründen."""
    return await UmbauService(db).detail(umbau_id)


@router.post(
    "/{umbau_id}/geraete/{device_id}/bestaetigen", response_model=GeraetErfassung
)
async def bestaetige_geraet(
    umbau_id: int,
    device_id: int,
    bestaetigt: bool = True,
    db: AsyncSession = Depends(get_db),
    username: str | None = Depends(get_username),
):
    """„Gerät vollständig erfasst“ setzen oder zurücknehmen. Nur in der Erfassung."""
    return await UmbauService(db).bestaetigen(umbau_id, device_id, bestaetigt, username)


@router.post("/{umbau_id}/einfrieren", response_model=UmbauDetail)
async def einfrieren(
    umbau_id: int,
    db: AsyncSession = Depends(get_db),
    username: str | None = Depends(get_username),
):
    """Friert den Soll-Stand ein: je physischem Stecker-Ende entsteht eine Zeile."""
    return await UmbauService(db).einfrieren(umbau_id, username)


@router.post("/{umbau_id}/status", response_model=UmbauDetail)
async def wechsle_status(
    umbau_id: int,
    wechsel: StatusWechsel,
    db: AsyncSession = Depends(get_db),
    username: str | None = Depends(get_username),
):
    return await UmbauService(db).status_wechsel(umbau_id, wechsel.ziel, username)


@router.post("/{umbau_id}/nachtraege", response_model=UmbauDetail)
async def nachtragen(
    umbau_id: int,
    eingabe: NachtragEingabe,
    db: AsyncSession = Depends(get_db),
    username: str | None = Depends(get_username),
):
    """Ein unbekanntes Kabel im Rückbau aufnehmen. Schreibt nur in den Umbau."""
    return await NachtragService(db).nachtragen(umbau_id, eingabe, username)


@router.delete("/{umbau_id}/nachtraege/{nachtrag_nr}", response_model=UmbauDetail)
async def nachtrag_entfernen(
    umbau_id: int,
    nachtrag_nr: int,
    db: AsyncSession = Depends(get_db),
    username: str | None = Depends(get_username),
):
    """Einen Nachtrag wieder entfernen, solange keines seiner Enden abgeklemmt ist."""
    return await NachtragService(db).entfernen(umbau_id, nachtrag_nr, username)


@router.put("/{umbau_id}/enden/{ende_id}/abklemmen", response_model=EndeOut)
async def abklemmen(
    umbau_id: int,
    ende_id: int,
    abgeklemmt: bool = True,
    db: AsyncSession = Depends(get_db),
    username: str | None = Depends(get_username),
):
    """Ein Ende abklemmen (nur im Rückbau); abgeklemmt=false nimmt es zurück."""
    return await EndenBuchung(db).abklemmen(umbau_id, ende_id, abgeklemmt, username)


@router.put("/{umbau_id}/enden/{ende_id}/anklemmen", response_model=EndeOut)
async def anklemmen(
    umbau_id: int,
    ende_id: int,
    eingabe: AnklemmenEingabe,
    db: AsyncSession = Depends(get_db),
    username: str | None = Depends(get_username),
):
    """Ein Ende anklemmen (nur im Wiederaufbau); anderer Port als Soll nur mit Grund."""
    return await EndenBuchung(db).anklemmen(umbau_id, ende_id, eingabe, username)
