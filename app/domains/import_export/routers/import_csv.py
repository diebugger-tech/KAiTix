import csv
import io
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import Rack, Device, Cable
from app.core.network_utils import normalize_ipv6

router = APIRouter()

VALID_DEVICE_TYPES = {
    "server",
    "switch",
    "pdu",
    "sonstige",
    "kentix_raconode",
    "kentix_doormaster",
    "kentix_multisensor",
    "patchpanel",
}

VALID_CABLE_TYPES = {
    "Cat6",
    "Cat6A",
    "Cat7",
    "DAC",
    "LC-LC",
    "SC-SC",
    "SFP+",
    "Strom-C13",
    "Strom-C19",
    "Strom-Schuko",
    "Strom-CEE-16A-3P",
    "Strom-CEE-32A-3P",
    "Strom-CEE-63A-3P",
    "sonstige",
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
                "ipv6_adresse": raw.get("ipv6_adresse") or None,
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
    row: Optional[int] = None
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
    ipv6_adresse: Optional[str] = None
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

    devs_res = await db.execute(select(Device))
    existing_map = {d.hostname.lower(): d for d in devs_res.scalars().all()}

    conflict_db = []
    conflict_csv = []
    conflict_rack = []
    seen_in_payload = set()
    existing_ipv6_map = {normalize_ipv6(d.ipv6_adresse): d.hostname.lower() for d in devs_res.scalars().all() if d.ipv6_adresse and normalize_ipv6(d.ipv6_adresse)}
    seen_ipv6_in_payload = {}

    # Build initial rack allocations
    updating_hostnames = (
        {r.hostname.lower() for r in payload.rows} if payload.update_mode else set()
    )
    rack_allocations: dict[int, list[tuple[int, int, str]]] = {}
    for dev in existing_map.values():
        if dev.hostname.lower() in updating_hostnames:
            continue
        if dev.rack_id and dev.u_position and dev.u_hoehe and dev.u_hoehe > 0:
            if dev.rack_id not in rack_allocations:
                rack_allocations[dev.rack_id] = []
            rack_allocations[dev.rack_id].append(
                (dev.u_position, dev.u_position + dev.u_hoehe - 1, dev.hostname)
            )

    for row_data in payload.rows:
        row_num = row_data.row or "?"
        name = row_data.hostname.lower()
        
        ipv6_norm = normalize_ipv6(row_data.ipv6_adresse) if row_data.ipv6_adresse else None
        
        if ipv6_norm:
            # Check for duplicates across all processing (update or create)
            if ipv6_norm in existing_ipv6_map and existing_ipv6_map[ipv6_norm] != name:
                conflict_db.append(f"Zeile {row_num}: IPv6 '{row_data.ipv6_adresse}' wird bereits von '{existing_ipv6_map[ipv6_norm]}' verwendet")
                continue
            if ipv6_norm in seen_ipv6_in_payload and seen_ipv6_in_payload[ipv6_norm] != name:
                conflict_csv.append(f"Zeile {row_num}: IPv6 '{row_data.ipv6_adresse}' mehrfach in Datei")
                continue
            seen_ipv6_in_payload[ipv6_norm] = name

        final_rack_id = row_data.rack_id
        final_u_pos = row_data.u_position
        final_u_hoehe = row_data.u_hoehe

        if payload.update_mode and name in existing_map:
            existing = existing_map[name]
            final_rack_id = (
                row_data.rack_id if row_data.rack_id is not None else existing.rack_id
            )
            final_u_pos = (
                row_data.u_position
                if row_data.u_position is not None
                else existing.u_position
            )

            existing.typ = (
                row_data.typ if row_data.typ in VALID_DEVICE_TYPES else "sonstige"
            )
            if row_data.rack_id is not None:
                existing.rack_id = row_data.rack_id
            if row_data.u_position is not None:
                existing.u_position = row_data.u_position
            existing.u_hoehe = row_data.u_hoehe
            if row_data.hersteller is not None:
                existing.hersteller = row_data.hersteller
            if row_data.modell is not None:
                existing.modell = row_data.modell
            if row_data.seriennummer is not None:
                existing.seriennummer = row_data.seriennummer
            if row_data.inventarnummer is not None:
                existing.inventarnummer = row_data.inventarnummer
            if row_data.ip_adresse is not None:
                existing.ip_adresse = row_data.ip_adresse
            if row_data.ipv6_adresse is not None:
                existing.ipv6_adresse = row_data.ipv6_adresse
            if row_data.bemerkung is not None:
                existing.bemerkung = row_data.bemerkung
            updated += 1
        else:
            if not payload.update_mode and name in existing_map:
                conflict_db.append(
                    f"Zeile {row_num}: '{row_data.hostname}' existiert bereits in der Datenbank"
                )
                continue

            if name in seen_in_payload:
                conflict_csv.append(
                    f"Zeile {row_num}: '{row_data.hostname}' mehrfach in Datei"
                )
                continue

            seen_in_payload.add(name)

            dev = Device(
                hostname=row_data.hostname,
                typ=row_data.typ if row_data.typ in VALID_DEVICE_TYPES else "sonstige",
                rack_id=row_data.rack_id,
                u_position=row_data.u_position,
                u_hoehe=row_data.u_hoehe,
                hersteller=row_data.hersteller,
                modell=row_data.modell,
                seriennummer=row_data.seriennummer,
                inventarnummer=row_data.inventarnummer,
                ip_adresse=row_data.ip_adresse,
                ipv6_adresse=row_data.ipv6_adresse,
                bemerkung=row_data.bemerkung,
            )
            db.add(dev)
            created += 1

        # Check for rack collision
        if final_rack_id and final_u_pos and final_u_hoehe and final_u_hoehe > 0:
            start_u = final_u_pos
            end_u = final_u_pos + final_u_hoehe - 1
            overlap = False
            for alloc_start, alloc_end, alloc_name in rack_allocations.get(
                final_rack_id, []
            ):
                if max(start_u, alloc_start) <= min(end_u, alloc_end):
                    conflict_rack.append(
                        f"Zeile {row_num}: '{row_data.hostname}' kollidiert mit '{alloc_name}' auf HE {max(start_u, alloc_start)}-{min(end_u, alloc_end)}"
                    )
                    overlap = True
                    break

            if not overlap:
                if final_rack_id not in rack_allocations:
                    rack_allocations[final_rack_id] = []
                rack_allocations[final_rack_id].append(
                    (start_u, end_u, row_data.hostname)
                )

    if conflict_db or conflict_csv or conflict_rack:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Import abgebrochen aufgrund von Konflikten",
                "conflicts": {
                    "db_duplicates": conflict_db,
                    "csv_duplicates": conflict_csv,
                    "rack_collisions": conflict_rack,
                },
            },
        )

    await db.commit()
    return {"created": created, "updated": updated}


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
    row: Optional[int] = None
    kabel_nr: Optional[str] = None
    typ: str = "sonstige"
    laenge_m: float = 1.0
    von_device_id: Optional[int] = None
    von_port: Optional[str] = None
    zu_device_id: Optional[int] = None
    zu_port: Optional[str] = None
    farbe: Optional[str] = None
    bemerkung: Optional[str] = None

    @field_validator("kabel_nr", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v


class CableCommitRequest(BaseModel):
    rows: List[CableImportRow]
    update_mode: bool = False


@router.post("/cables/commit")
async def commit_cables(
    payload: CableCommitRequest, db: AsyncSession = Depends(get_db)
):
    created = 0
    updated = 0

    cables_res = await db.execute(select(Cable))
    existing_map = {
        c.kabel_nr.lower(): c for c in cables_res.scalars().all() if c.kabel_nr
    }

    conflict_db = []
    conflict_csv = []
    seen_in_payload = set()

    for row_data in payload.rows:
        row_num = row_data.row or "?"
        kabel_nr = row_data.kabel_nr
        name = kabel_nr.lower() if kabel_nr else None

        if payload.update_mode and name and name in existing_map:
            existing = existing_map[name]
            existing.typ = row_data.typ if row_data.typ in VALID_CABLE_TYPES else "Cat6"
            existing.laenge_m = float(row_data.laenge_m)
            existing.farbe = row_data.farbe
            existing.bemerkung = row_data.bemerkung
            existing.von_device_id = row_data.von_device_id
            existing.nach_device_id = row_data.zu_device_id
            existing.von_port = row_data.von_port
            existing.nach_port = row_data.zu_port
            updated += 1
            continue

        if row_data.kabel_nr and name:
            if not payload.update_mode and name in existing_map:
                conflict_db.append(
                    f"Zeile {row_num}: Kabel-Nr '{row_data.kabel_nr}' existiert bereits"
                )
                continue
            if name in seen_in_payload:
                conflict_csv.append(
                    f"Zeile {row_num}: Kabel-Nr '{row_data.kabel_nr}' mehrfach in Datei"
                )
                continue
            seen_in_payload.add(name)

        cable = Cable(
            kabel_nr=row_data.kabel_nr,
            typ=row_data.typ if row_data.typ in VALID_CABLE_TYPES else "Cat6",
            laenge_m=Decimal(str(row_data.laenge_m)),
            farbe=row_data.farbe,
            bemerkung=row_data.bemerkung,
            von_port=row_data.von_port,
            nach_port=row_data.zu_port,
            von_device_id=row_data.von_device_id,
            nach_device_id=row_data.zu_device_id,
        )

        db.add(cable)
        created += 1

    if conflict_db or conflict_csv:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Import abgebrochen aufgrund von Konflikten",
                "conflicts": {
                    "db_duplicates": conflict_db,
                    "csv_duplicates": conflict_csv,
                },
            },
        )

    await db.commit()
    return {"created": created, "updated": updated}
