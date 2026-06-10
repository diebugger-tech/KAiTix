import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models import (
    Cable as CableModel,
    Device as DeviceModel,
    Rack as RackModel,
    PduOutlet as PduOutletModel,
)
from app.domains.cabling.schemas import CableCreate, CableUpdate
from dataclasses import dataclass

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


@dataclass
class TopologyRaw:
    racks: Sequence[RackModel]
    devices: Sequence[DeviceModel]
    cables: Sequence[CableModel]
    outlets: Sequence[PduOutletModel]
    dev_map: dict[int, DeviceModel]
    rack_map: dict[int, RackModel]


class CablingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def load_topology(self) -> TopologyRaw:
        racks = (
            (
                await self.db.execute(
                    select(RackModel).options(selectinload(RackModel.devices))
                )
            )
            .scalars()
            .all()
        )
        devices = (await self.db.execute(select(DeviceModel))).scalars().all()
        cables = (
            (
                await self.db.execute(
                    select(CableModel).options(
                        selectinload(CableModel.von_device),
                        selectinload(CableModel.nach_device),
                    )
                )
            )
            .scalars()
            .all()
        )
        outlets = (await self.db.execute(select(PduOutletModel))).scalars().all()

        return TopologyRaw(
            racks=racks,
            devices=devices,
            cables=cables,
            outlets=outlets,
            dev_map={d.id: d for d in devices},
            rack_map={r.id: r for r in racks},
        )

    @staticmethod
    def build_edges(raw: TopologyRaw) -> list[dict]:
        edges = []
        for cable in raw.cables:
            if cable.von_device_id and cable.nach_device_id:
                vd = raw.dev_map.get(cable.von_device_id)
                nd = raw.dev_map.get(cable.nach_device_id)
                cross_rack = bool(
                    vd and nd and vd.rack_id and nd.rack_id and vd.rack_id != nd.rack_id
                )
                edges.append(
                    {
                        "id": f"cable-{cable.id}",
                        "edge_type": "cable",
                        "kabel_nr": cable.kabel_nr,
                        "typ": cable.typ,
                        "laenge_m": float(cable.laenge_m) if cable.laenge_m else None,
                        "farbe": cable.farbe,
                        "von_device_id": cable.von_device_id,
                        "von_port": cable.von_port,
                        "nach_device_id": cable.nach_device_id,
                        "nach_port": cable.nach_port,
                        "cross_rack": cross_rack,
                    }
                )

        for outlet in raw.outlets:
            if outlet.pdu_id and outlet.connected_device_id:
                pdu = raw.dev_map.get(outlet.pdu_id)
                dev = raw.dev_map.get(outlet.connected_device_id)
                cross_rack = bool(
                    pdu
                    and dev
                    and pdu.rack_id
                    and dev.rack_id
                    and pdu.rack_id != dev.rack_id
                )
                edges.append(
                    {
                        "id": f"power-{outlet.id}",
                        "edge_type": "power",
                        "kabel_nr": outlet.outlet_name,
                        "typ": f"Strom-{outlet.steckdosentyp or 'PDU'}",
                        "laenge_m": None,
                        "farbe": None,
                        "von_device_id": outlet.pdu_id,
                        "von_port": outlet.outlet_name,
                        "nach_device_id": outlet.connected_device_id,
                        "nach_port": outlet.connected_port,
                        "cross_rack": cross_rack,
                        "phase": outlet.phase,
                    }
                )

        return edges

    @staticmethod
    def build_racks_out(raw: TopologyRaw) -> list[dict]:
        return [
            {
                "id": r.id,
                "name": r.name,
                "standort": r.standort,
                "rackreihe": r.rackreihe,
                "hoehe_u": r.hoehe_u,
            }
            for r in raw.racks
        ]

    # Cable color rules
    @staticmethod
    def load_color_rules() -> Dict[str, Any]:
        return _load_color_rules()

    @staticmethod
    def update_color_rules(rules_payload: Dict[str, Any]) -> Dict[str, Any]:
        if "rules" not in rules_payload:
            raise HTTPException(
                status_code=400, detail="Missing 'rules' array in payload"
            )
        data = _load_color_rules()
        data["rules"] = rules_payload["rules"]
        _save_color_rules(data)
        return data

    @staticmethod
    def suggest_color(typ: str) -> Dict[str, str]:
        suggested = CABLE_TYPE_TO_DEFAULT_COLOR.get(typ, "")
        if not suggested:
            raise HTTPException(status_code=400, detail=f"Unknown cable type: {typ}")
        return {
            "typ": typ,
            "suggested_color": suggested,
            "note": "Default per KAiTix color scheme",
        }

    # Cables operations
    async def list_cables(self) -> List[CableModel]:
        result = await self.db.execute(
            select(CableModel).options(selectinload(CableModel.cable_strands))
        )
        return result.scalars().all()  # type: ignore

    async def create_cable(self, cable_in: CableCreate) -> CableModel:
        if not cable_in.kabel_nr:
            count_result = await self.db.execute(
                select(func.count()).select_from(CableModel)
            )
            count = count_result.scalar() or 0
            cable_in.kabel_nr = f"KAB-{count + 1:04d}"
        data = cable_in.model_dump()
        db_cable = CableModel(**data)
        self.db.add(db_cable)
        await self.db.commit()

        # Reload with strands
        result = await self.db.execute(
            select(CableModel)
            .where(CableModel.id == db_cable.id)
            .options(selectinload(CableModel.cable_strands))
        )
        return result.scalar_one()

    async def get_cable(self, cable_id: int) -> CableModel:
        result = await self.db.execute(
            select(CableModel)
            .where(CableModel.id == cable_id)
            .options(selectinload(CableModel.cable_strands))
        )
        cable = result.scalar_one_or_none()
        if not cable:
            raise HTTPException(status_code=404, detail="Cable not found")
        return cable

    async def update_cable(
        self, cable_id: int, cable_in: CableUpdate, username: str | None
    ) -> CableModel:
        result = await self.db.execute(
            select(CableModel).where(CableModel.id == cable_id)
        )
        cable = result.scalar_one_or_none()
        if not cable:
            raise HTTPException(status_code=404, detail="Cable not found")

        update_data = cable_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(cable, field, value)
        cable.geaendert_von = username
        cable.geaendert_am = datetime.now(timezone.utc)

        await self.db.commit()
        # Reload with strands
        result = await self.db.execute(
            select(CableModel)
            .where(CableModel.id == cable.id)
            .options(selectinload(CableModel.cable_strands))
        )
        return result.scalar_one()

    async def delete_cable(self, cable_id: int) -> None:
        result = await self.db.execute(
            select(CableModel).where(CableModel.id == cable_id)
        )
        cable = result.scalar_one_or_none()
        if not cable:
            raise HTTPException(status_code=404, detail="Cable not found")
        await self.db.delete(cable)
        await self.db.commit()

    async def trace_cable(self, cable_id: int) -> Dict[str, Any]:
        start_res = await self.db.execute(
            select(CableModel).where(CableModel.id == cable_id)
        )
        start = start_res.scalar_one_or_none()
        if not start:
            raise HTTPException(status_code=404, detail="Kabel nicht gefunden")

        all_res = await self.db.execute(select(CableModel))
        all_cables = all_res.scalars().all()

        devs_res = await self.db.execute(select(DeviceModel))
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

        def _hop(device_id: int | None, exclude_cable_id: int):
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

        path = [_cable_dict(start)]

        # Expand right
        cur = start
        for _ in range(MAX_HOPS):
            nxt = _hop(cur.nach_device_id, cur.id)
            if not nxt:
                break
            path.append(_cable_dict(nxt))
            cur = nxt

        # Expand left
        cur = start
        for _ in range(MAX_HOPS):
            prv = _hop(cur.von_device_id, cur.id)
            if not prv:
                break
            path.insert(0, _cable_dict(prv))
            cur = prv

        return {"trace": path, "hops": len(path)}

    async def search(self, q: str) -> Dict[str, List[Dict[str, Any]]]:
        q = q.strip()
        if len(q) < 2:
            return {"devices": [], "cables": [], "racks": []}

        term = f"%{q}%"
        MAX_RESULTS = 8

        devs_res = await self.db.execute(
            select(DeviceModel)
            .where(
                or_(
                    DeviceModel.hostname.ilike(term),
                    DeviceModel.ip_adresse.ilike(term),
                    DeviceModel.seriennummer.ilike(term),
                    DeviceModel.inventarnummer.ilike(term),
                    DeviceModel.hersteller.ilike(term),
                    DeviceModel.modell.ilike(term),
                )
            )
            .limit(MAX_RESULTS)
        )
        devs = devs_res.scalars().all()

        cables_res = await self.db.execute(
            select(CableModel)
            .where(
                or_(
                    CableModel.kabel_nr.ilike(term),
                    CableModel.farbe.ilike(term),
                    CableModel.von_port.ilike(term),
                    CableModel.nach_port.ilike(term),
                    CableModel.bemerkung.ilike(term),
                )
            )
            .limit(MAX_RESULTS)
        )
        cables = cables_res.scalars().all()

        racks_res = await self.db.execute(
            select(RackModel)
            .where(or_(RackModel.name.ilike(term), RackModel.standort.ilike(term)))
            .limit(MAX_RESULTS)
        )
        racks = racks_res.scalars().all()

        return {
            "devices": [
                {
                    "id": d.id,
                    "hostname": d.hostname,
                    "typ": d.typ,
                    "rack_id": d.rack_id,
                    "ip_adresse": d.ip_adresse,
                    "hersteller": d.hersteller,
                    "modell": d.modell,
                }
                for d in devs
            ],
            "cables": [
                {
                    "id": c.id,
                    "kabel_nr": c.kabel_nr,
                    "typ": c.typ,
                    "farbe": c.farbe,
                    "von_port": c.von_port,
                    "nach_port": c.nach_port,
                }
                for c in cables
            ],
            "racks": [
                {"id": r.id, "name": r.name, "standort": r.standort} for r in racks
            ],
        }
