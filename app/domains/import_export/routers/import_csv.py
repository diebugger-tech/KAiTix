import csv
import io
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.models import Rack, Device, Cable

router = APIRouter()

VALID_DEVICE_TYPES = {
    "server",
    "switch",
    "pdu",
    "sonstige",
    "kentix_raconode",
    "kentix_doormaster",
    "kentix_multisensor",
}


def _parse_csv(content: bytes) -> List[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for i, row in enumerate(reader, start=2):
        rows.append(
            {"_row": i, **{k.strip(): (v or "").strip() for k, v in row.items() if k}}
        )
    return rows


# ── Geräte Preview ────────────────────────────────────────────────────────────


@router.post("/devices/preview")
async def preview_devices(file: UploadFile, db: AsyncSession = Depends(get_db)):
    content = await file.read()
    raw_rows = _parse_csv(content)

    racks_res = await db.execute(select(Rack))
    rack_map = {r.name.lower(): r for r in racks_res.scalars().all()}

    devs_res = await db.execute(select(Device))
    existing = {d.hostname.lower() for d in devs_res.scalars().all()}

    result = []
    for raw in raw_rows:
        errors: List[str] = []
        hostname = raw.get("hostname", "")
        typ = raw.get("typ", "server").lower()
        rack_name = raw.get("rack", "")

        if not hostname:
            errors.append("hostname fehlt")
        if typ not in VALID_DEVICE_TYPES:
            errors.append(f"Unbekannter Typ '{typ}'")

        rack_obj = rack_map.get(rack_name.lower()) if rack_name else None
        if rack_name and not rack_obj:
            errors.append(f"Rack '{rack_name}' nicht gefunden")

        try:
            u_pos = int(raw.get("u_position") or 0) or None
        except ValueError:
            u_pos = None
            errors.append("u_position muss Ganzzahl sein")

        try:
            u_hoehe = int(raw.get("u_hoehe") or 1)
        except ValueError:
            u_hoehe = 1

        status = (
            "error" if errors else ("exists" if hostname.lower() in existing else "new")
        )

        result.append(
            {
                "row": raw["_row"],
                "hostname": hostname,
                "typ": typ,
                "rack": rack_name,
                "rack_id": rack_obj.id if rack_obj else None,
                "u_position": u_pos,
                "u_hoehe": u_hoehe,
                "hersteller": raw.get("hersteller") or None,
                "modell": raw.get("modell") or None,
                "seriennummer": raw.get("seriennummer") or None,
                "inventarnummer": raw.get("inventarnummer") or None,
                "ip_adresse": raw.get("ip_adresse") or None,
                "bemerkung": raw.get("bemerkung") or None,
                "status": status,
                "errors": errors,
            }
        )

    return {
        "rows": result,
        "total": len(result),
        "new": sum(1 for r in result if r["status"] == "new"),
        "exists": sum(1 for r in result if r["status"] == "exists"),
        "error_count": sum(1 for r in result if r["status"] == "error"),
    }


# ── Geräte Commit ─────────────────────────────────────────────────────────────


class DeviceImportRow(BaseModel):
    hostname: str
    typ: str
    rack_id: Optional[int] = None
    u_position: Optional[int] = None
    u_hoehe: int = 1
    hersteller: Optional[str] = None
    modell: Optional[str] = None
    seriennummer: Optional[str] = None
    inventarnummer: Optional[str] = None
    ip_adresse: Optional[str] = None
    bemerkung: Optional[str] = None


class DeviceCommitRequest(BaseModel):
    rows: List[DeviceImportRow]
    update_mode: bool = False


@router.post("/devices/commit")
async def commit_devices(
    payload: DeviceCommitRequest, db: AsyncSession = Depends(get_db)
):
    created = 0
    updated = 0
    skipped = 0

    existing_map: dict[str, Device] = {}
    if payload.update_mode:
        devs_res = await db.execute(select(Device))
        existing_map = {d.hostname.lower(): d for d in devs_res.scalars().all()}

    for row in payload.rows:
        if payload.update_mode:
            existing = existing_map.get(row.hostname.lower())
            if existing:
                existing.typ = row.typ if row.typ in VALID_DEVICE_TYPES else "sonstige"
                if row.rack_id is not None:
                    existing.rack_id = row.rack_id
                if row.u_position is not None:
                    existing.u_position = row.u_position
                existing.u_hoehe = row.u_hoehe
                if row.hersteller is not None:
                    existing.hersteller = row.hersteller
                if row.modell is not None:
                    existing.modell = row.modell
                if row.seriennummer is not None:
                    existing.seriennummer = row.seriennummer
                if row.inventarnummer is not None:
                    existing.inventarnummer = row.inventarnummer
                if row.ip_adresse is not None:
                    existing.ip_adresse = row.ip_adresse
                if row.bemerkung is not None:
                    existing.bemerkung = row.bemerkung
                updated += 1
                continue

        dev = Device(
            hostname=row.hostname,
            typ=row.typ if row.typ in VALID_DEVICE_TYPES else "sonstige",
            rack_id=row.rack_id,
            u_position=row.u_position,
            u_hoehe=row.u_hoehe,
            hersteller=row.hersteller,
            modell=row.modell,
            seriennummer=row.seriennummer,
            inventarnummer=row.inventarnummer,
            ip_adresse=row.ip_adresse,
            bemerkung=row.bemerkung,
        )
        # Use savepoint so IntegrityError only rolls back this one row,
        # not the entire session (BUG-03 fix)
        try:
            async with db.begin_nested():
                db.add(dev)
                await db.flush()
            created += 1
        except IntegrityError:
            skipped += 1
    await db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}


# ── Kabel Preview ─────────────────────────────────────────────────────────────


@router.post("/cables/preview")
async def preview_cables(file: UploadFile, db: AsyncSession = Depends(get_db)):
    content = await file.read()
    raw_rows = _parse_csv(content)

    devs_res = await db.execute(select(Device))
    dev_map = {d.hostname.lower(): d for d in devs_res.scalars().all()}

    cables_res = await db.execute(select(Cable))
    cable_nr_map = {
        c.kabel_nr.lower(): c for c in cables_res.scalars().all() if c.kabel_nr
    }

    result = []
    for raw in raw_rows:
        errors: List[str] = []
        von_name = raw.get("von_geraet", "")
        zu_name = raw.get("zu_geraet", "")
        kabel_nr = raw.get("kabel_nr") or None

        try:
            laenge = float(raw.get("laenge_m") or 1.0)
        except ValueError:
            laenge = 1.0
            errors.append("laenge_m muss Zahl sein")

        von_dev = dev_map.get(von_name.lower()) if von_name else None
        zu_dev = dev_map.get(zu_name.lower()) if zu_name else None

        if von_name and not von_dev:
            errors.append(f"Gerät '{von_name}' nicht gefunden")
        if zu_name and not zu_dev:
            errors.append(f"Gerät '{zu_name}' nicht gefunden")

        cable_exists = bool(kabel_nr and kabel_nr.lower() in cable_nr_map)
        status = "error" if errors else ("exists" if cable_exists else "new")

        result.append(
            {
                "row": raw["_row"],
                "kabel_nr": kabel_nr,
                "typ": raw.get("typ") or "sonstige",
                "laenge_m": laenge,
                "von_geraet": von_name or None,
                "von_device_id": von_dev.id if von_dev else None,
                "von_port": raw.get("von_port") or None,
                "zu_geraet": zu_name or None,
                "zu_device_id": zu_dev.id if zu_dev else None,
                "zu_port": raw.get("zu_port") or None,
                "farbe": raw.get("farbe") or None,
                "bemerkung": raw.get("bemerkung") or None,
                "status": status,
                "errors": errors,
            }
        )

    return {
        "rows": result,
        "total": len(result),
        "new": sum(1 for r in result if r["status"] == "new"),
        "exists": sum(1 for r in result if r["status"] == "exists"),
        "error_count": sum(1 for r in result if r["status"] == "error"),
    }


# ── Kabel Commit ──────────────────────────────────────────────────────────────


class CableImportRow(BaseModel):
    kabel_nr: Optional[str] = None
    typ: str = "sonstige"
    laenge_m: float = 1.0
    von_device_id: Optional[int] = None
    von_port: Optional[str] = None
    zu_device_id: Optional[int] = None
    zu_port: Optional[str] = None
    farbe: Optional[str] = None
    bemerkung: Optional[str] = None


class CableCommitRequest(BaseModel):
    rows: List[CableImportRow]
    update_mode: bool = False


@router.post("/cables/commit")
async def commit_cables(
    payload: CableCommitRequest, db: AsyncSession = Depends(get_db)
):
    created = 0
    updated = 0
    skipped = 0

    existing_map: dict[str, Cable] = {}
    if payload.update_mode:
        cables_res = await db.execute(select(Cable))
        existing_map = {
            c.kabel_nr.lower(): c for c in cables_res.scalars().all() if c.kabel_nr
        }

    for row in payload.rows:
        if payload.update_mode and row.kabel_nr:
            existing = existing_map.get(row.kabel_nr.lower())
            if existing:
                existing.typ = row.typ
                existing.laenge_m = Decimal(str(row.laenge_m))
                existing.von_device_id = row.von_device_id
                existing.von_port = row.von_port
                existing.nach_device_id = row.zu_device_id
                existing.nach_port = row.zu_port
                existing.farbe = row.farbe
                existing.bemerkung = row.bemerkung
                updated += 1
                continue

        cable = Cable(
            kabel_nr=row.kabel_nr,
            typ=row.typ,
            laenge_m=Decimal(str(row.laenge_m)),
            von_device_id=row.von_device_id,
            von_port=row.von_port,
            nach_device_id=row.zu_device_id,
            nach_port=row.zu_port,
            farbe=row.farbe,
            bemerkung=row.bemerkung,
        )
        # Use savepoint so a duplicate kabel_nr only skips this one cable,
        # not the entire batch (BUG-04 fix)
        try:
            async with db.begin_nested():
                db.add(cable)
                await db.flush()
            created += 1
        except IntegrityError:
            skipped += 1
    await db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}
