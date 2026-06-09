import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, status
from pydantic import BaseModel
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models import Rack, Device, Interface, Cable
from app.domains.import_export.services.eplan_parser import EplanParser

router = APIRouter()


class ConnectionImport(BaseModel):
    cable_number: Optional[str] = None
    cable_type: Optional[str] = None
    length: Optional[float] = None
    farbe: Optional[str] = None
    source_rack: Optional[str] = None
    source_device: Optional[str] = None
    source_port: Optional[str] = None
    target_rack: Optional[str] = None
    target_device: Optional[str] = None
    target_port: Optional[str] = None


class ImportCommitRequest(BaseModel):
    connections: List[ConnectionImport]


@router.post("/preview")
async def preview_eplan(
    file: UploadFile, mapping_json: str = Form(...), db: AsyncSession = Depends(get_db)
):
    """
    Parses an uploaded E-Plan CSV file based on the mapping dictionary and returns a validation preview.
    """
    try:
        mapping = json.loads(mapping_json)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid mapping_json format. Must be a valid JSON string.",
        )

    default_mapping = {
        "cable_number": "Kabelnummer",
        "cable_type": "Typ",
        "length": "Länge",
        "farbe": "Farbe",
        "source_rack": "Quelle Rack",
        "source_device": "Quelle Gerät",
        "source_port": "Quelle Port",
        "target_rack": "Ziel Rack",
        "target_device": "Ziel Gerät",
        "target_port": "Ziel Port",
    }
    if not mapping:
        mapping = default_mapping
    else:
        mapping = {**default_mapping, **mapping}

    content = await file.read()
    parsed = EplanParser.parse_csv(content, mapping)
    preview = await EplanParser.preview_import(parsed, db)
    return preview


@router.post("/commit", status_code=status.HTTP_201_CREATED)
async def commit_eplan(
    payload: ImportCommitRequest, db: AsyncSession = Depends(get_db)
):
    """
    Commits parsed connections to the database. Creates missing racks, devices, and ports on-the-fly.
    """
    imported_cables_count = 0
    created_racks_count = 0
    created_devices_count = 0
    created_ports_count = 0

    # We cache fetched entities during this transaction to avoid redundant DB queries
    racks_cache = {}
    devices_cache = {}
    device_ports_cache = {}

    # Pre-fetch existing racks
    r_result = await db.execute(select(Rack))
    for r in r_result.scalars().all():
        racks_cache[r.name.lower()] = r

    # Pre-fetch existing devices with their ports
    from sqlalchemy.orm import selectinload

    d_result = await db.execute(select(Device).options(selectinload(Device.interfaces)))
    for d in d_result.scalars().all():
        devices_cache[d.hostname.lower()] = d
        device_ports_cache[d.hostname.lower()] = list(d.interfaces)

    for conn in payload.connections:
        # Reset per-iteration variables to prevent stale scope from previous iteration (BUG-02)
        s_dev_key: str | None = None
        t_dev_key: str | None = None
        # Determine source and target devices, racks, ports
        # 1. Resolve source rack
        s_rack = None
        if conn.source_rack:
            s_rack_key = conn.source_rack.lower()
            if s_rack_key in racks_cache:
                s_rack = racks_cache[s_rack_key]
            else:
                s_rack = Rack(name=conn.source_rack, standort="Imported")
                db.add(s_rack)
                await db.flush()  # get ID
                racks_cache[s_rack_key] = s_rack
                created_racks_count += 1

        # 2. Resolve target rack
        t_rack = None
        if conn.target_rack:
            t_rack_key = conn.target_rack.lower()
            if t_rack_key in racks_cache:
                t_rack = racks_cache[t_rack_key]
            else:
                t_rack = Rack(name=conn.target_rack, standort="Imported")
                db.add(t_rack)
                await db.flush()
                racks_cache[t_rack_key] = t_rack
                created_racks_count += 1

        # 3. Resolve source device
        s_dev = None
        if conn.source_device:
            s_dev_key = conn.source_device.lower()
            if s_dev_key in devices_cache:
                s_dev = devices_cache[s_dev_key]
            else:
                s_dev_lower = conn.source_device.lower()
                dev_typ = "server"
                if "sw" in s_dev_lower or "switch" in s_dev_lower:
                    dev_typ = "switch"
                elif "pdu" in s_dev_lower:
                    dev_typ = "pdu"
                elif "usv" in s_dev_lower:
                    dev_typ = "usv"
                elif "patchpanel" in s_dev_lower or "pp" in s_dev_lower:
                    dev_typ = "patchpanel"

                s_dev = Device(
                    hostname=conn.source_device,
                    typ=dev_typ,
                    rack_id=s_rack.id if s_rack else None,
                    u_hoehe=0 if dev_typ == "pdu" else 1,
                )
                db.add(s_dev)
                await db.flush()
                devices_cache[s_dev_key] = s_dev
                device_ports_cache[s_dev_key] = []
                created_devices_count += 1

        # 4. Resolve target device
        t_dev = None
        if conn.target_device:
            t_dev_key = conn.target_device.lower()
            if t_dev_key in devices_cache:
                t_dev = devices_cache[t_dev_key]
            else:
                t_dev_lower = conn.target_device.lower()
                dev_typ = "server"
                if "sw" in t_dev_lower or "switch" in t_dev_lower:
                    dev_typ = "switch"
                elif "pdu" in t_dev_lower:
                    dev_typ = "pdu"
                elif "usv" in t_dev_lower:
                    dev_typ = "usv"
                elif "patchpanel" in t_dev_lower or "pp" in t_dev_lower:
                    dev_typ = "patchpanel"

                t_dev = Device(
                    hostname=conn.target_device,
                    typ=dev_typ,
                    rack_id=t_rack.id if t_rack else None,
                    u_hoehe=0 if dev_typ == "pdu" else 1,
                )
                db.add(t_dev)
                await db.flush()
                devices_cache[t_dev_key] = t_dev
                device_ports_cache[t_dev_key] = []
                created_devices_count += 1

        # 5. Resolve source port
        s_port = None
        if s_dev and conn.source_port:
            s_port_name_lower = conn.source_port.lower()
            s_ports_list = device_ports_cache[s_dev_key]
            s_port = next(
                (p for p in s_ports_list if p.port_name.lower() == s_port_name_lower),
                None,
            )
            if not s_port:
                # Determine port type (LC, SC, RJ45) based on name or cable type
                port_typ = "RJ45"
                if conn.cable_type and any(
                    kw in conn.cable_type.lower()
                    for kw in ["lwl", "fiber", "lc", "sc", "opt"]
                ):
                    port_typ = "LC" if "lc" in conn.cable_type.lower() else "SC"
                s_port = Interface(
                    device_id=s_dev.id,
                    port_name=conn.source_port,
                    typ=port_typ,
                    status="frei",
                )
                db.add(s_port)
                await db.flush()
                s_ports_list.append(s_port)
                created_ports_count += 1

        # 6. Resolve target port
        t_port = None
        if t_dev and conn.target_port:
            t_port_name_lower = conn.target_port.lower()
            t_ports_list = device_ports_cache[t_dev_key]
            t_port = next(
                (p for p in t_ports_list if p.port_name.lower() == t_port_name_lower),
                None,
            )
            if not t_port:
                port_typ = "RJ45"
                if conn.cable_type and any(
                    kw in conn.cable_type.lower()
                    for kw in ["lwl", "fiber", "lc", "sc", "opt"]
                ):
                    port_typ = "LC" if "lc" in conn.cable_type.lower() else "SC"
                t_port = Interface(
                    device_id=t_dev.id,
                    port_name=conn.target_port,
                    typ=port_typ,
                    status="frei",
                )
                db.add(t_port)
                await db.flush()
                t_ports_list.append(t_port)
                created_ports_count += 1

        # 7. Create/Update Cable
        if conn.cable_number:
            cable_num = conn.cable_number
            # Check if cable exists in db
            c_query = select(Cable).where(Cable.kabel_nr == cable_num)
            c_result = await db.execute(c_query)
            cable = c_result.scalar_one_or_none()

            length_val = (
                Decimal(str(conn.length)) if conn.length is not None else Decimal("0.0")
            )

            # Map input cable type to valid database enum option
            raw_typ = conn.cable_type
            db_typ = "sonstige"
            if raw_typ:
                raw_lower = raw_typ.lower()
                if "cat6a" in raw_lower:
                    db_typ = "Cat6A"
                elif "cat6" in raw_lower:
                    db_typ = "Cat6"
                elif "cat7" in raw_lower:
                    db_typ = "Cat7"
                elif "dac" in raw_lower:
                    db_typ = "DAC"
                elif "lc" in raw_lower:
                    db_typ = "LC-LC"
                elif "sc" in raw_lower:
                    db_typ = "SC-SC"
                elif "sfp+" in raw_lower:
                    db_typ = "SFP+"
                elif "c13" in raw_lower:
                    db_typ = "Strom-C13"
                elif "c19" in raw_lower:
                    db_typ = "Strom-C19"
                elif "schuko" in raw_lower:
                    db_typ = "Strom-Schuko"
                elif "cee-16a" in raw_lower or "cee 16a" in raw_lower:
                    db_typ = "Strom-CEE-16A-3P"
                elif "cee-32a" in raw_lower or "cee 32a" in raw_lower:
                    db_typ = "Strom-CEE-32A-3P"
                elif "cee-63a" in raw_lower or "cee 63a" in raw_lower:
                    db_typ = "Strom-CEE-63A-3P"
                elif raw_typ in [
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
                ]:
                    db_typ = raw_typ

            if not cable:
                cable = Cable(
                    kabel_nr=cable_num,
                    typ=db_typ,
                    laenge_m=length_val,
                    farbe=conn.farbe,
                    von_device_id=s_dev.id if s_dev else None,
                    von_port=conn.source_port,
                    nach_device_id=t_dev.id if t_dev else None,
                    nach_port=conn.target_port,
                )
                db.add(cable)
                await db.flush()
                imported_cables_count += 1
            else:
                # Update existing cable attributes
                cable.typ = db_typ
                if conn.length is not None:
                    cable.laenge_m = length_val
                if conn.farbe:
                    cable.farbe = conn.farbe
                cable.von_device_id = s_dev.id if s_dev else cable.von_device_id
                cable.von_port = conn.source_port or cable.von_port
                cable.nach_device_id = t_dev.id if t_dev else cable.nach_device_id
                cable.nach_port = conn.target_port or cable.nach_port
                imported_cables_count += 1

            # If this is a power cable, configure PDU / USV properties on the target device
            if db_typ.startswith("Strom-") and t_dev:
                # Force typ to pdu if the device hostname indicates it is a PDU
                if "pdu" in t_dev.hostname.lower() and t_dev.typ != "pdu":
                    t_dev.typ = "pdu"
                    t_dev.u_hoehe = 0
                elif "usv" in t_dev.hostname.lower() and t_dev.typ != "usv":
                    t_dev.typ = "usv"

                # Extract redundancy path
                red_path = None
                if conn.cable_number and "-PDU-A-" in conn.cable_number.upper():
                    red_path = "A"
                elif conn.cable_number and "-PDU-B-" in conn.cable_number.upper():
                    red_path = "B"
                elif "-A-" in t_dev.hostname.upper() or t_dev.hostname.upper().endswith("-A"):
                    red_path = "A"
                elif "-B-" in t_dev.hostname.upper() or t_dev.hostname.upper().endswith("-B"):
                    red_path = "B"

                if red_path:
                    t_dev.redundancy_path = red_path
                    if t_dev.typ == "pdu" and t_dev.side is None:
                        t_dev.side = "left" if red_path == "A" else "right"

                # Parse and set power values based on cable type
                if "cee-16a" in db_typ.lower():
                    t_dev.absicherung_a = Decimal("16.0")
                    t_dev.strom_typ = "3-phasig"
                    t_dev.anschluss_stecker = "CEE-16A-3P"
                    t_dev.spannung_v = 400
                elif "cee-32a" in db_typ.lower():
                    t_dev.absicherung_a = Decimal("32.0")
                    t_dev.strom_typ = "3-phasig"
                    t_dev.anschluss_stecker = "CEE-32A-3P"
                    t_dev.spannung_v = 400
                elif "cee-63a" in db_typ.lower():
                    t_dev.absicherung_a = Decimal("63.0")
                    t_dev.strom_typ = "3-phasig"
                    t_dev.anschluss_stecker = "CEE-63A-3P"
                    t_dev.spannung_v = 400
                elif "c13" in db_typ.lower():
                    t_dev.absicherung_a = Decimal("10.0")
                    t_dev.strom_typ = "1-phasig"
                    t_dev.anschluss_stecker = "C14"
                    t_dev.spannung_v = 230
                elif "c19" in db_typ.lower():
                    t_dev.absicherung_a = Decimal("16.0")
                    t_dev.strom_typ = "1-phasig"
                    t_dev.anschluss_stecker = "C20"
                    t_dev.spannung_v = 230
                elif "schuko" in db_typ.lower():
                    t_dev.absicherung_a = Decimal("16.0")
                    t_dev.strom_typ = "1-phasig"
                    t_dev.anschluss_stecker = "Schuko"
                    t_dev.spannung_v = 230

                # Set min_rack_hoehe for vertical Kentix PDUs
                if t_dev.typ == "pdu" and t_dev.min_rack_hoehe is None:
                    if "40he" in t_dev.hostname.lower():
                        t_dev.min_rack_hoehe = 40
                    elif "42he" in t_dev.hostname.lower():
                        t_dev.min_rack_hoehe = 42
                    elif "47he" in t_dev.hostname.lower():
                        t_dev.min_rack_hoehe = 47

            # Update port occupancy and link cable
            if s_port:
                s_port.status = "belegt"
                s_port.kabel_id = cable.id
            if t_port:
                t_port.status = "belegt"
                t_port.kabel_id = cable.id

    await db.commit()

    return {
        "status": "success",
        "imported_cables": imported_cables_count,
        "created_racks": created_racks_count,
        "created_devices": created_devices_count,
        "created_ports": created_ports_count,
    }
