"""
Hardware Type Catalog API
Manages a catalog of hardware types that can be installed in racks.
Stored in JSON file (no DB migration required).
"""

import json
import os
import tempfile
import threading
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

_hardware_lock = threading.Lock()

router = APIRouter()

DATA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data")
)
HARDWARE_FILE = os.path.join(DATA_DIR, "hardware_types.json")


# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)


class HardwareType(BaseModel):
    id: int
    name: str
    kategorie: str  # server, switch, firewall, storage, pdu, kvm, usv, sonstige, rack
    hersteller: str = ""
    modell: str = ""
    u_hoehe: int = Field(1, ge=0)
    tdp_watt: Optional[int] = Field(None, ge=0)
    psu_count: Optional[int] = Field(None, ge=0)
    psu_nennwatt: Optional[int] = Field(None, ge=0)
    breite_mm: Optional[int] = Field(None, ge=0)
    tiefe_mm: Optional[int] = Field(None, ge=0)
    port_count_rj45: int = Field(0, ge=0)
    port_count_lwl: int = Field(0, ge=0)
    port_count_sfp: int = Field(0, ge=0)
    min_rack_hoehe: int = Field(0, ge=0)
    leistung_kw: Optional[float] = Field(None, ge=0)
    n1_faehig: Optional[bool] = None
    bemerkung: str = ""

    model_config = ConfigDict(from_attributes=True)


class HardwareTypeCreate(BaseModel):
    name: str
    kategorie: str = "server"
    hersteller: str = ""
    modell: str = ""
    u_hoehe: int = Field(1, ge=0)
    tdp_watt: Optional[int] = Field(None, ge=0)
    psu_count: Optional[int] = Field(None, ge=0)
    psu_nennwatt: Optional[int] = Field(None, ge=0)
    breite_mm: Optional[int] = Field(None, ge=0)
    tiefe_mm: Optional[int] = Field(None, ge=0)
    port_count_rj45: int = Field(0, ge=0)
    port_count_lwl: int = Field(0, ge=0)
    port_count_sfp: int = Field(0, ge=0)
    min_rack_hoehe: int = Field(0, ge=0)
    leistung_kw: Optional[float] = Field(None, ge=0)
    n1_faehig: Optional[bool] = None
    bemerkung: str = ""


class HardwareTypeUpdate(BaseModel):
    name: Optional[str] = None
    kategorie: Optional[str] = None
    hersteller: Optional[str] = None
    modell: Optional[str] = None
    u_hoehe: Optional[int] = Field(None, ge=0)
    tdp_watt: Optional[int] = Field(None, ge=0)
    psu_count: Optional[int] = Field(None, ge=0)
    psu_nennwatt: Optional[int] = Field(None, ge=0)
    breite_mm: Optional[int] = Field(None, ge=0)
    tiefe_mm: Optional[int] = Field(None, ge=0)
    port_count_rj45: Optional[int] = Field(None, ge=0)
    port_count_lwl: Optional[int] = Field(None, ge=0)
    port_count_sfp: Optional[int] = Field(None, ge=0)
    min_rack_hoehe: Optional[int] = Field(None, ge=0)
    leistung_kw: Optional[float] = Field(None, ge=0)
    n1_faehig: Optional[bool] = None
    bemerkung: Optional[str] = None


def _load_hardware() -> List[dict]:
    if not os.path.exists(HARDWARE_FILE):
        # Seed with default hardware types
        defaults = [
            {
                "id": 1,
                "name": "Rack-Server 1HE",
                "kategorie": "server",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 1,
                "tdp_watt": 250,
                "port_count_rj45": 2,
                "port_count_lwl": 0,
                "port_count_sfp": 0,
                "bemerkung": "",
            },
            {
                "id": 2,
                "name": "Rack-Server 2HE",
                "kategorie": "server",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 2,
                "tdp_watt": 450,
                "port_count_rj45": 4,
                "port_count_lwl": 0,
                "port_count_sfp": 2,
                "bemerkung": "",
            },
            {
                "id": 3,
                "name": "Rack-Server 4HE",
                "kategorie": "server",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 4,
                "tdp_watt": 800,
                "port_count_rj45": 4,
                "port_count_lwl": 0,
                "port_count_sfp": 4,
                "bemerkung": "",
            },
            {
                "id": 4,
                "name": "Blade-Chassis",
                "kategorie": "server",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 10,
                "tdp_watt": 3000,
                "port_count_rj45": 8,
                "port_count_lwl": 0,
                "port_count_sfp": 8,
                "bemerkung": "Modulares Server-Gehäuse",
            },
            {
                "id": 5,
                "name": "Storage-Array / JBOD",
                "kategorie": "storage",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 2,
                "tdp_watt": 400,
                "port_count_rj45": 2,
                "port_count_lwl": 0,
                "port_count_sfp": 4,
                "bemerkung": "Dedizierte Festplatten-/SSD-Erweiterung",
            },
            {
                "id": 6,
                "name": "NAS/SAN-Controller",
                "kategorie": "storage",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 2,
                "tdp_watt": 350,
                "port_count_rj45": 4,
                "port_count_lwl": 0,
                "port_count_sfp": 4,
                "bemerkung": "Speicher-Steuereinheit",
            },
            {
                "id": 7,
                "name": "Firewall",
                "kategorie": "firewall",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 1,
                "tdp_watt": 150,
                "port_count_rj45": 6,
                "port_count_lwl": 0,
                "port_count_sfp": 2,
                "bemerkung": "Netzwerksicherheits-Appliance",
            },
            {
                "id": 8,
                "name": "Core-Switch",
                "kategorie": "switch",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 1,
                "tdp_watt": 200,
                "port_count_rj45": 24,
                "port_count_lwl": 0,
                "port_count_sfp": 4,
                "bemerkung": "",
            },
            {
                "id": 9,
                "name": "Access-Switch",
                "kategorie": "switch",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 1,
                "tdp_watt": 100,
                "port_count_rj45": 48,
                "port_count_lwl": 0,
                "port_count_sfp": 2,
                "bemerkung": "",
            },
            {
                "id": 10,
                "name": "Router",
                "kategorie": "switch",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 1,
                "tdp_watt": 120,
                "port_count_rj45": 4,
                "port_count_lwl": 0,
                "port_count_sfp": 4,
                "bemerkung": "WAN-Anbindung",
            },
            {
                "id": 11,
                "name": "Load Balancer",
                "kategorie": "switch",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 1,
                "tdp_watt": 180,
                "port_count_rj45": 8,
                "port_count_lwl": 0,
                "port_count_sfp": 2,
                "bemerkung": "Lastverteilung",
            },
            {
                "id": 12,
                "name": "KVM-Konsole",
                "kategorie": "kvm",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 1,
                "tdp_watt": 30,
                "port_count_rj45": 1,
                "port_count_lwl": 0,
                "port_count_sfp": 0,
                "bemerkung": "Ausziehbare Monitor-Tastatur-Schublade",
            },
            {
                "id": 13,
                "name": "KVM-Switch",
                "kategorie": "kvm",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 1,
                "tdp_watt": 25,
                "port_count_rj45": 1,
                "port_count_lwl": 0,
                "port_count_sfp": 0,
                "bemerkung": "Elektronischer Umschalter",
            },
            {
                "id": 14,
                "name": "Rack-Monitoring",
                "kategorie": "sonstige",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 1,
                "tdp_watt": 20,
                "port_count_rj45": 1,
                "port_count_lwl": 0,
                "port_count_sfp": 0,
                "bemerkung": "Sensor-Auswertung",
            },
            {
                "id": 15,
                "name": "Intelligente PDU",
                "kategorie": "pdu",
                "hersteller": "",
                "modell": "",
                "u_hoehe": 1,
                "tdp_watt": 0,
                "port_count_rj45": 1,
                "port_count_lwl": 0,
                "port_count_sfp": 0,
                "bemerkung": "Stromleiste mit Netzwerk-Controller",
            },
        ]
        _save_hardware(defaults)
        return defaults
    with open(HARDWARE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_hardware(data: List[dict]) -> None:
    with _hardware_lock:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".json.tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, HARDWARE_FILE)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


@router.get("/", response_model=List[HardwareType])
async def list_hardware(kategorie: Optional[str] = None):
    """List all hardware types, optionally filtered by category."""
    items = _load_hardware()
    if kategorie == "rack":
        racks = [i for i in items if i.get("kategorie") == "rack"]
        if not racks:
            rittal_racks = [
                {
                    "id": 25,
                    "name": "Rittal VX IT 42HE",
                    "kategorie": "rack",
                    "hersteller": "Rittal",
                    "modell": "VX IT 42HE",
                    "u_hoehe": 42,
                    "breite_mm": 800,
                    "tiefe_mm": 1000,
                    "min_rack_hoehe": 0,
                    "tdp_watt": None,
                    "bemerkung": "Kentix SmartPDU 40HE kompatibel",
                },
                {
                    "id": 26,
                    "name": "Rittal VX IT 47HE",
                    "kategorie": "rack",
                    "hersteller": "Rittal",
                    "modell": "VX IT 47HE",
                    "u_hoehe": 47,
                    "breite_mm": 800,
                    "tiefe_mm": 1000,
                    "min_rack_hoehe": 0,
                    "tdp_watt": None,
                    "bemerkung": "Kentix SmartPDU 47HE kompatibel",
                },
                {
                    "id": 27,
                    "name": "Rittal TS IT 42HE",
                    "kategorie": "rack",
                    "hersteller": "Rittal",
                    "modell": "TS IT 42HE",
                    "u_hoehe": 42,
                    "breite_mm": 800,
                    "tiefe_mm": 1000,
                    "min_rack_hoehe": 0,
                    "tdp_watt": None,
                    "bemerkung": "Kentix SmartPDU 40HE kompatibel",
                },
                {
                    "id": 28,
                    "name": "Rittal TS IT 47HE",
                    "kategorie": "rack",
                    "hersteller": "Rittal",
                    "modell": "TS IT 47HE",
                    "u_hoehe": 47,
                    "breite_mm": 800,
                    "tiefe_mm": 1000,
                    "min_rack_hoehe": 0,
                    "tdp_watt": None,
                    "bemerkung": "Kentix SmartPDU 47HE kompatibel",
                },
            ]
            items.extend(rittal_racks)
            _save_hardware(items)
    if kategorie:
        items = [i for i in items if i.get("kategorie") == kategorie]
    return items


@router.post("/", response_model=HardwareType)
async def create_hardware(data: HardwareTypeCreate):
    """Create a new hardware type."""
    items = _load_hardware()
    new_id = max((i["id"] for i in items), default=0) + 1
    item = {"id": new_id, **data.model_dump()}
    items.append(item)
    _save_hardware(items)
    return item


@router.get("/{hardware_id}", response_model=HardwareType)
async def get_hardware(hardware_id: int):
    """Get a single hardware type by ID."""
    items = _load_hardware()
    for item in items:
        if item["id"] == hardware_id:
            return item
    raise HTTPException(status_code=404, detail="Hardware type not found")


@router.put("/{hardware_id}", response_model=HardwareType)
async def update_hardware(hardware_id: int, data: HardwareTypeUpdate):
    """Update an existing hardware type."""
    items = _load_hardware()
    for item in items:
        if item["id"] == hardware_id:
            for key, value in data.model_dump(exclude_unset=True).items():
                item[key] = value
            _save_hardware(items)
            return item
    raise HTTPException(status_code=404, detail="Hardware type not found")


@router.delete("/{hardware_id}")
async def delete_hardware(hardware_id: int):
    """Delete a hardware type."""
    items = _load_hardware()
    filtered = [i for i in items if i["id"] != hardware_id]
    if len(filtered) == len(items):
        raise HTTPException(status_code=404, detail="Hardware type not found")
    _save_hardware(filtered)
    return {"ok": True}
