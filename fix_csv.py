import re

with open("app/domains/import_export/routers/import_csv.py", "r") as f:
    content = f.read()

# Make sure HTTPException is imported
if "from fastapi import APIRouter, Depends, UploadFile, HTTPException" not in content:
    content = content.replace("from fastapi import APIRouter, Depends, UploadFile", "from fastapi import APIRouter, Depends, UploadFile, HTTPException")

# Patch DeviceImportRow
content = content.replace(
    "class DeviceImportRow(BaseModel):",
    "class DeviceImportRow(BaseModel):\n    row: Optional[int] = None"
)

# Patch CableImportRow
content = content.replace(
    "class CableImportRow(BaseModel):",
    "class CableImportRow(BaseModel):\n    row: Optional[int] = None"
)

# Patch commit_devices
old_commit_devices = """@router.post("/devices/commit")
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
    return {"created": created, "updated": updated, "skipped": skipped}"""

new_commit_devices = """@router.post("/devices/commit")
async def commit_devices(
    payload: DeviceCommitRequest, db: AsyncSession = Depends(get_db)
):
    created = 0
    updated = 0

    devs_res = await db.execute(select(Device))
    existing_map = {d.hostname.lower(): d for d in devs_res.scalars().all()}
    
    conflict_db = []
    conflict_csv = []
    seen_in_payload = set()

    for row_data in payload.rows:
        row_num = row_data.row or "?"
        name = row_data.hostname.lower()

        if payload.update_mode and name in existing_map:
            existing = existing_map[name]
            existing.typ = row_data.typ if row_data.typ in VALID_DEVICE_TYPES else "sonstige"
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
            if row_data.bemerkung is not None:
                existing.bemerkung = row_data.bemerkung
            updated += 1
            continue
            
        if not payload.update_mode and name in existing_map:
            conflict_db.append(f"Zeile {row_num}: '{row_data.hostname}' existiert bereits in der Datenbank")
            continue
            
        if name in seen_in_payload:
            conflict_csv.append(f"Zeile {row_num}: '{row_data.hostname}' mehrfach in Datei")
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
            bemerkung=row_data.bemerkung,
        )
        db.add(dev)
        created += 1

    if conflict_db or conflict_csv:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Import abgebrochen aufgrund von Konflikten",
                "conflicts": {"db_duplicates": conflict_db, "csv_duplicates": conflict_csv}
            }
        )

    await db.commit()
    return {"created": created, "updated": updated}"""

content = content.replace(old_commit_devices, new_commit_devices)


# Patch commit_cables
old_commit_cables = """@router.post("/cables/commit")
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
    return {"created": created, "updated": updated, "skipped": skipped}"""

new_commit_cables = """@router.post("/cables/commit")
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
        name = row_data.kabel_nr.lower() if row_data.kabel_nr else None

        if payload.update_mode and name and name in existing_map:
            existing = existing_map[name]
            existing.typ = row_data.typ
            existing.laenge_m = Decimal(str(row_data.laenge_m))
            existing.von_device_id = row_data.von_device_id
            existing.von_port = row_data.von_port
            existing.nach_device_id = row_data.zu_device_id
            existing.nach_port = row_data.zu_port
            existing.farbe = row_data.farbe
            existing.bemerkung = row_data.bemerkung
            updated += 1
            continue

        if name:
            if not payload.update_mode and name in existing_map:
                conflict_db.append(f"Zeile {row_num}: Kabel-Nr '{row_data.kabel_nr}' existiert bereits in der Datenbank")
                continue
            if name in seen_in_payload:
                conflict_csv.append(f"Zeile {row_num}: Kabel-Nr '{row_data.kabel_nr}' mehrfach in Datei")
                continue
            seen_in_payload.add(name)

        cable = Cable(
            kabel_nr=row_data.kabel_nr,
            typ=row_data.typ,
            laenge_m=Decimal(str(row_data.laenge_m)),
            von_device_id=row_data.von_device_id,
            von_port=row_data.von_port,
            nach_device_id=row_data.zu_device_id,
            nach_port=row_data.zu_port,
            farbe=row_data.farbe,
            bemerkung=row_data.bemerkung,
        )
        db.add(cable)
        created += 1

    if conflict_db or conflict_csv:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Import abgebrochen aufgrund von Konflikten",
                "conflicts": {"db_duplicates": conflict_db, "csv_duplicates": conflict_csv}
            }
        )

    await db.commit()
    return {"created": created, "updated": updated}"""

content = content.replace(old_commit_cables, new_commit_cables)

with open("app/domains/import_export/routers/import_csv.py", "w") as f:
    f.write(content)
