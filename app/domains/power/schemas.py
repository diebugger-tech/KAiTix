from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from datetime import datetime



# === USV MODULE SCHEMAS ===
class UsvModuleBase(BaseModel):
    usv_unit_id: int
    slot: int = Field(..., ge=0)
    leistung_kw: Decimal = Field(..., gt=0)
    status: str = "aktiv"
    seriennummer: Optional[str] = None


class UsvModuleCreate(UsvModuleBase):
    pass


class UsvModuleUpdate(BaseModel):
    slot: Optional[int] = Field(None, ge=0)
    leistung_kw: Optional[Decimal] = Field(None, gt=0)
    status: Optional[str] = None
    seriennummer: Optional[str] = None


class UsvModule(UsvModuleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# === USV UNIT SCHEMAS ===
class UsvUnitBase(BaseModel):
    bezeichnung: str
    hersteller: str = "Wöhrle SVS"
    rack_id: int
    max_kw: Decimal = Field(..., gt=0)


class UsvUnitCreate(UsvUnitBase):
    pass


class UsvUnitUpdate(BaseModel):
    bezeichnung: Optional[str] = None
    hersteller: Optional[str] = None
    rack_id: Optional[int] = None
    max_kw: Optional[Decimal] = Field(None, gt=0)


class UsvUnit(UsvUnitBase):
    id: int
    modules: List[UsvModule] = []
    model_config = ConfigDict(from_attributes=True)


# === USV SIMULATION EVENT SCHEMAS ===
class UsvSimulationEventResponse(BaseModel):
    id: int
    timestamp: datetime
    event_type: str
    severity: str
    description: str
    usv_unit_id: Optional[int] = None
    snapshot_json: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

