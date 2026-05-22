from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal


# === CABLE STRAND SCHEMAS ===
class CableStrandBase(BaseModel):
    cable_id: int
    strand_number: int
    farbe: Optional[str] = None
    von_port_id: Optional[int] = None
    nach_port_id: Optional[int] = None
    bemerkung: Optional[str] = None


class CableStrandCreate(CableStrandBase):
    pass


class CableStrandUpdate(BaseModel):
    strand_number: Optional[int] = None
    farbe: Optional[str] = None
    von_port_id: Optional[int] = None
    nach_port_id: Optional[int] = None
    bemerkung: Optional[str] = None


class CableStrand(CableStrandBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# === CABLE SCHEMAS ===
class CableBase(BaseModel):
    kabel_nr: Optional[str] = None
    typ: str
    laenge_m: Decimal = Field(..., ge=0)
    farbe: Optional[str] = None
    von_device_id: Optional[int] = None
    nach_device_id: Optional[int] = None
    verlegt_am: Optional[date] = None
    verlegt_von: Optional[str] = None
    bemerkung: Optional[str] = None


class CableCreate(CableBase):
    kabel_nr: Optional[str] = None


class CableUpdate(BaseModel):
    kabel_nr: Optional[str] = None
    typ: Optional[str] = None
    laenge_m: Optional[Decimal] = Field(None, ge=0)
    farbe: Optional[str] = None
    von_device_id: Optional[int] = None
    nach_device_id: Optional[int] = None
    verlegt_am: Optional[date] = None
    verlegt_von: Optional[str] = None
    bemerkung: Optional[str] = None


class Cable(CableBase):
    id: int
    cable_strands: List[CableStrand] = []
    geaendert_von: Optional[str] = None
    geaendert_am: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# === INTERFACE SCHEMAS (Replaces ServerInterface & DevicePort) ===
class InterfaceBody(BaseModel):
    port_name: str
    typ: str = "1GbE"
    mac_adresse: Optional[str] = None


class InterfaceBase(BaseModel):
    device_id: int
    port_name: str
    typ: str
    status: str = "frei"
    mac_adresse: Optional[str] = None
    kabel_id: Optional[int] = None


class InterfaceCreate(InterfaceBase):
    pass


class InterfaceUpdate(BaseModel):
    port_name: Optional[str] = None
    typ: Optional[str] = None
    status: Optional[str] = None
    mac_adresse: Optional[str] = None
    kabel_id: Optional[int] = None


class Interface(InterfaceBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
