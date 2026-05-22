import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.deps import get_username
from app.models import Cable as CableModel
from app.schemas import Cable, CableCreate, CableUpdate

_COLOR_RULES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "cable_color_rules.json"
)


def _load_color_rules() -> Dict[str, Any]:
    if os.path.exists(_COLOR_RULES_PATH):
        with open(_COLOR_RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "1.0", "last_updated": "", "rules": []}


def _save_color_rules(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_COLOR_RULES_PATH), exist_ok=True)
    with open(_COLOR_RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


router = APIRouter()


CABLE_TYPE_TO_DEFAULT_COLOR: Dict[str, str] = {
    "Cat6": "Blau",
    "Cat6A": "Blau",
    "Cat7": "Blau",
    "DAC": "Grau",
    "LC-LC": "Erika-Violett",
    "SC-SC": "Erika-Violett",
    "SFP+": "Grau",
    "Strom-C13": "Rot",
    "Strom-C19": "Rot",
    "Strom-Schuko": "Rot",
    "sonstige": "",
}

CABLE_COLOR_LEGEND: Dict[str, Any] = {
    "meta": {
        "title": "KAiTix RZ-Farbcode-Legende",
        "standards": ["DIN EN 50173-1", "TIA-598", "VDE 0100"],
        "version": "1.0",
    },
    "categories": [
        {
            "id": "lwl",
            "name": "Glasfaser (LWL)",
            "standard": "DIN EN 50173-1 / TIA-598",
            "description": "Mantelfarbe definiert den Fasertyp nach internationalem Standard.",
            "items": [
                {
                    "color": "Gelb",
                    "hex": "#FACC15",
                    "meaning": "Singlemode OS1 / OS2",
                    "usage": "Lange Strecken, Carrier-Anbindung, Gebäude-Backbone",
                },
                {
                    "color": "Erika-Violett",
                    "hex": "#C026D3",
                    "meaning": "Multimode OM4",
                    "usage": "Aktueller Standard für interne High-Speed-Verbindungen (10G/40G/100G)",
                },
                {
                    "color": "Lindgrün",
                    "hex": "#84CC16",
                    "meaning": "Multimode OM5",
                    "usage": "Modernste Multimode-Faser (SWDM / Wellenlängen-Multiplex)",
                },
                {
                    "color": "Aqua (Türkis)",
                    "hex": "#22D3EE",
                    "meaning": "Multimode OM3",
                    "usage": "Ältere Netze (10 Gbit/s), wird in neuen RZs kaum noch verbaut",
                },
                {
                    "color": "Orange",
                    "hex": "#FB923C",
                    "meaning": "Multimode OM1 / OM2",
                    "usage": "Veraltet, nur noch in historischen Altsystemen",
                },
            ],
        },
        {
            "id": "power",
            "name": "Stromversorgung (A/B-Pfade)",
            "standard": "Internes RZ-Schema",
            "description": "Strikte Farbtrennung für redundante USV-Stromkreise. Jeder Server mit zwei Netzteilen bekommt immer ein Kabel Pfad A und eines Pfad B.",
            "items": [
                {
                    "color": "Rot",
                    "hex": "#EF4444",
                    "meaning": "Strompfad A (USV-A)",
                    "usage": "PDU-A, primärer Stromkreis",
                    "warning": "Nie beide Netzteile in dieselbe Farbschiene stecken!",
                },
                {
                    "color": "Schwarz",
                    "hex": "#171717",
                    "meaning": "Strompfad B (USV-B)",
                    "usage": "PDU-B, redundanter Stromkreis",
                    "warning": "Nie beide Netzteile in dieselbe Farbschiene stecken!",
                },
                {
                    "color": "Blau",
                    "hex": "#3B82F6",
                    "meaning": "Strompfad A (Alternative)",
                    "usage": "PDU-A in modernen RZ-Farbschemata",
                },
                {
                    "color": "Weiß",
                    "hex": "#F3F4F6",
                    "meaning": "Strompfad B (Alternative)",
                    "usage": "PDU-B in modernen RZ-Farbschemata",
                },
            ],
        },
        {
            "id": "copper",
            "name": "Kupfer-Datenkabel (Ethernet)",
            "standard": "Internes RZ-Schema",
            "description": "Farbcodierung für Patchkabel und strukturierte Verkabelung, um die Netzwerkfunktion auf einen Blick zu erkennen.",
            "items": [
                {
                    "color": "Grün",
                    "hex": "#22C55E",
                    "meaning": "Management-Netzwerk",
                    "usage": "IPMI, iLO, iDRAC, KVM, Out-of-Band-Fernwartung",
                },
                {
                    "color": "Blau",
                    "hex": "#3B82F6",
                    "meaning": "Primäres Datennetzwerk (LAN)",
                    "usage": "Produktions-Traffic, Server-LAN, User-Netz",
                },
                {
                    "color": "Gelb",
                    "hex": "#EAB308",
                    "meaning": "Storage Area Network (SAN)",
                    "usage": "Speicher-Verbindungen, iSCSI, Fibre Channel over Copper",
                },
                {
                    "color": "Orange",
                    "hex": "#FB923C",
                    "meaning": "Uplinks / DMZ / Sicherheitszonen",
                    "usage": "Core-Switch-Uplinks, demilitarisierte Zone, WAN-Anbindung",
                },
                {
                    "color": "Violett",
                    "hex": "#A855F7",
                    "meaning": "Telefonie / Gebäudetechnik",
                    "usage": "VoIP, Kameras, Zeiterfassung, HVAC-Steuerung",
                },
                {
                    "color": "Weiß",
                    "hex": "#F3F4F6",
                    "meaning": "Telefonie / Gebäudetechnik (Alternative)",
                    "usage": "VoIP, Kameras, Zeiterfassung, HVAC-Steuerung",
                },
            ],
        },
        {
            "id": "ground",
            "name": "Erdung & Potenzialausgleich",
            "standard": "VDE 0100-540 / IEC 60446",
            "description": "Gesetzlich vorgeschriebene Farbcodierung für Schutzleiter — ausschließlich Grün-Gelb.",
            "items": [
                {
                    "color": "Grün-Gelb",
                    "hex": "#65A30D",
                    "meaning": "Schutzleiter (PE)",
                    "usage": "Erdung von Serverracks, Kabeltrassen, PDUs, Gehäusen",
                    "warning": "Ausschließlich für Erdung — niemals für Signale oder Strom verwenden!",
                },
            ],
        },
        {
            "id": "dac",
            "name": "Direct Attach Copper (DAC)",
            "standard": "Hersteller-üblich",
            "description": "Twinax-Kupferkabel für ultrakurze ToR-Verbindungen. Farbe ist herstellerabhängig, oft grau oder schwarz.",
            "items": [
                {
                    "color": "Grau",
                    "hex": "#9CA3AF",
                    "meaning": "DAC Passiv / Aktiv",
                    "usage": "Switch-zu-Server (< 7m), ToR-Verbindungen",
                },
                {
                    "color": "Schwarz",
                    "hex": "#171717",
                    "meaning": "DAC Aktiv",
                    "usage": "Längere Twinax-Verbindungen innerhalb des Racks",
                },
            ],
        },
    ],
    "best_practice": (
        "In Ihrer Dokumentation sollten Sie eine feste Legende definieren und konsequent anwenden. "
        "Ein bewährtes Schema in deutschen Rechenzentren: Management = Grün, LAN = Blau, "
        "SAN = Gelb, Strom A = Rot, Strom B = Schwarz, Singlemode = Gelb, OM4 = Erika-Violett."
    ),
}


@router.get("/legend", response_model=Dict[str, Any])
async def get_cable_color_legend():
    """
    Returns the standardized data center cable color coding legend.
    Covers fiber optics (DIN EN 50173-1), power paths, copper ethernet,
    grounding (VDE), and DAC conventions.
    """
    return CABLE_COLOR_LEGEND


@router.get("/suggest-color")
async def suggest_cable_color(typ: str):
    """
    Suggests a default cable color based on the cable type.
    Returns the recommended color per industry standard.
    """
    suggested = CABLE_TYPE_TO_DEFAULT_COLOR.get(typ, "")
    if not suggested:
        raise HTTPException(status_code=400, detail=f"Unknown cable type: {typ}")
    return {
        "typ": typ,
        "suggested_color": suggested,
        "note": "Default per KAiTix color scheme",
    }


@router.get("/color-rules", response_model=Dict[str, Any])
async def get_color_rules():
    """
    Returns the project-specific cable color rules from JSON storage.
    Used by frontend for admin editing and by suggest-color as fallback.
    """
    return _load_color_rules()


@router.put("/color-rules", response_model=Dict[str, Any])
async def update_color_rules(rules_payload: Dict[str, Any]):
    """
    Updates the cable color rules JSON file.
    Expects: {"rules": [...]} with rule objects containing id, typ, standard_farbe, etc.
    """
    if "rules" not in rules_payload:
        raise HTTPException(status_code=400, detail="Missing 'rules' array in payload")

    data = _load_color_rules()
    data["rules"] = rules_payload["rules"]
    _save_color_rules(data)
    return data


@router.get("/", response_model=List[Cable])
async def list_cables(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CableModel).options(selectinload(CableModel.cable_strands))
    )
    return result.scalars().all()


@router.post("/", response_model=Cable, status_code=status.HTTP_201_CREATED)
async def create_cable(cable_in: CableCreate, db: AsyncSession = Depends(get_db)):
    if not cable_in.kabel_nr:
        count_result = await db.execute(select(func.count()).select_from(CableModel))
        count = count_result.scalar() or 0
        cable_in.kabel_nr = f"KAB-{count + 1:04d}"
    data = cable_in.model_dump()
    db_cable = CableModel(**data)
    db.add(db_cable)
    await db.commit()
    await db.refresh(db_cable)
    # Reload with strands
    result = await db.execute(
        select(CableModel)
        .where(CableModel.id == db_cable.id)
        .options(selectinload(CableModel.cable_strands))
    )
    return result.scalar_one()


@router.get("/{cable_id}", response_model=Cable)
async def get_cable(cable_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CableModel)
        .where(CableModel.id == cable_id)
        .options(selectinload(CableModel.cable_strands))
    )
    cable = result.scalar_one_or_none()
    if not cable:
        raise HTTPException(status_code=404, detail="Cable not found")
    return cable


@router.put("/{cable_id}", response_model=Cable)
async def update_cable(
    cable_id: int,
    cable_in: CableUpdate,
    db: AsyncSession = Depends(get_db),
    username: str | None = Depends(get_username),
):
    result = await db.execute(select(CableModel).where(CableModel.id == cable_id))
    cable = result.scalar_one_or_none()
    if not cable:
        raise HTTPException(status_code=404, detail="Cable not found")

    update_data = cable_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cable, field, value)
    cable.geaendert_von = username
    cable.geaendert_am = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(cable)
    # Reload with strands
    result = await db.execute(
        select(CableModel)
        .where(CableModel.id == cable.id)
        .options(selectinload(CableModel.cable_strands))
    )
    return result.scalar_one()


@router.delete("/{cable_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cable(cable_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CableModel).where(CableModel.id == cable_id))
    cable = result.scalar_one_or_none()
    if not cable:
        raise HTTPException(status_code=404, detail="Cable not found")
    await db.delete(cable)
    await db.commit()
    return None


@router.get("/{cable_id}/trace")
async def trace_cable(cable_id: int, db: AsyncSession = Depends(get_db)):
    """Follow cable chain left and right through endpoint devices (max 20 hops)."""
    start_res = await db.execute(select(CableModel).where(CableModel.id == cable_id))
    start = start_res.scalar_one_or_none()
    if not start:
        raise HTTPException(status_code=404, detail="Kabel nicht gefunden")

    all_res = await db.execute(select(CableModel))
    all_cables = all_res.scalars().all()

    from app.models import Device as DeviceModel

    devs_res = await db.execute(select(DeviceModel))
    dev_map = {d.id: d for d in devs_res.scalars().all()}

    # Build cable lookup: device_id → [cable, ...]
    dev_to_cables: dict[int, list] = {}
    for c in all_cables:
        if c.von_device_id:
            dev_to_cables.setdefault(c.von_device_id, []).append(c)
        if c.nach_device_id:
            dev_to_cables.setdefault(c.nach_device_id, []).append(c)

    MAX_HOPS = 20
    visited_cables: set[int] = {start.id}

    def _hop(device_id: int | None, exclude_cable_id: int) -> list[dict] | None:
        """Find one unvisited cable connected to device_id (not exclude_cable_id)."""
        if not device_id:
            return None
        for c in dev_to_cables.get(device_id, []):
            if c.id not in visited_cables and c.id != exclude_cable_id:
                visited_cables.add(c.id)
                return c
        return None

    def _cable_dict(c) -> dict:
        vd = dev_map.get(c.von_device_id) if c.von_device_id else None
        nd = dev_map.get(c.nach_device_id) if c.nach_device_id else None
        return {
            "id": c.id,
            "kabel_nr": c.kabel_nr,
            "typ": c.typ,
            "laenge_m": float(c.laenge_m) if c.laenge_m else None,
            "farbe": c.farbe,
            "von_device_id": c.von_device_id,
            "von_device_hostname": vd.hostname if vd else None,
            "von_port": c.von_port,
            "nach_device_id": c.nach_device_id,
            "nach_device_hostname": nd.hostname if nd else None,
            "nach_port": c.nach_port,
        }

    # Grow path: [left..., start, ...right]
    path = [_cable_dict(start)]

    # Expand right: follow cables from nach_device_id
    cur = start
    for _ in range(MAX_HOPS):
        nxt = _hop(cur.nach_device_id, cur.id)
        if not nxt:
            break
        path.append(_cable_dict(nxt))
        cur = nxt

    # Expand left: follow cables from von_device_id of start
    cur = start
    for _ in range(MAX_HOPS):
        prv = _hop(cur.von_device_id, cur.id)
        if not prv:
            break
        path.insert(0, _cable_dict(prv))
        cur = prv

    return {"trace": path, "hops": len(path)}
