from datetime import date, datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from decimal import Decimal

from app.domains.cabling.models import Cable as _CableModel

# Erlaubte Werte für kabeltypen.alt_typ: genau die Werte des Enums cables.typ,
# weil alt_typ beim Speichern eines Kabels nach cables.typ geschrieben wird.
ALT_TYP_WERTE: tuple[str, ...] = tuple(_CableModel.__table__.c.typ.type.enums)
MAX_ENDEN_JE_SEITE = 64

KabeltypKategorie = Literal[
    "kupfer", "lwl", "dac", "aoc", "breakout", "strom", "sonstige"
]


def _pruefe_alt_typ(wert: Optional[str]) -> Optional[str]:
    if wert is not None and wert not in ALT_TYP_WERTE:
        raise ValueError(
            f"alt_typ '{wert}' ist kein gültiger Kabeltyp. "
            f"Erlaubt: {', '.join(ALT_TYP_WERTE)}"
        )
    return wert


# === KABELTYP SCHEMAS ===
class KabeltypBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    kategorie: KabeltypKategorie
    stecker_a: str = Field(..., min_length=1, max_length=50)
    stecker_b: str = Field(..., min_length=1, max_length=50)
    enden_a: int = Field(1, ge=1, le=MAX_ENDEN_JE_SEITE)
    enden_b: int = Field(1, ge=1, le=MAX_ENDEN_JE_SEITE)
    standard_farbe: Optional[str] = Field(None, max_length=30)
    alt_typ: str = "sonstige"
    aktiv: bool = True


class KabeltypCreate(KabeltypBase):
    _alt_typ_gueltig = field_validator("alt_typ")(_pruefe_alt_typ)


class KabeltypUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    kategorie: Optional[KabeltypKategorie] = None
    stecker_a: Optional[str] = Field(None, min_length=1, max_length=50)
    stecker_b: Optional[str] = Field(None, min_length=1, max_length=50)
    enden_a: Optional[int] = Field(None, ge=1, le=MAX_ENDEN_JE_SEITE)
    enden_b: Optional[int] = Field(None, ge=1, le=MAX_ENDEN_JE_SEITE)
    standard_farbe: Optional[str] = Field(None, max_length=30)
    alt_typ: Optional[str] = None
    aktiv: Optional[bool] = None

    _alt_typ_gueltig = field_validator("alt_typ")(_pruefe_alt_typ)


class Kabeltyp(KabeltypBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class KabeltypKurz(BaseModel):
    """Auszug des Kabeltyps, der an jedem Kabel mitgeliefert wird."""

    id: int
    name: str
    kategorie: str
    enden_a: int
    enden_b: int
    model_config = ConfigDict(from_attributes=True)


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
    kabeltyp_id: Optional[int] = None
    laenge_m: Decimal = Field(..., ge=0)
    farbe: Optional[str] = None
    von_device_id: Optional[int] = None
    von_port: Optional[str] = Field(None, max_length=50)
    nach_device_id: Optional[int] = None
    nach_port: Optional[str] = Field(None, max_length=50)
    verlegt_am: Optional[date] = None
    verlegt_von: Optional[str] = None
    bemerkung: Optional[str] = None


class CableCreate(CableBase):
    kabel_nr: Optional[str] = None
    # Neue Clients schicken kabeltyp_id, alte nur typ. Eines von beiden ist Pflicht.
    typ: Optional[str] = None

    @model_validator(mode="after")
    def _typ_oder_kabeltyp(self) -> "CableCreate":
        if self.kabeltyp_id is None and not self.typ:
            raise ValueError("Entweder kabeltyp_id oder typ muss angegeben werden")
        return self


class CableUpdate(BaseModel):
    kabel_nr: Optional[str] = None
    typ: Optional[str] = None
    kabeltyp_id: Optional[int] = None
    laenge_m: Optional[Decimal] = Field(None, ge=0)
    farbe: Optional[str] = None
    von_device_id: Optional[int] = None
    von_port: Optional[str] = Field(None, max_length=50)
    nach_device_id: Optional[int] = None
    nach_port: Optional[str] = Field(None, max_length=50)
    verlegt_am: Optional[date] = None
    verlegt_von: Optional[str] = None
    bemerkung: Optional[str] = None


class Cable(CableBase):
    id: int
    typ: str
    kabeltyp: Optional[KabeltypKurz] = None
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
