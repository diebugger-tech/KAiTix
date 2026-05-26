from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal


# === RACK SCHEMAS ===
class RackBase(BaseModel):
    name: str
    standort: str
    rackreihe: Optional[str] = None
    hoehe_u: int = Field(42, ge=1)
    breite_mm: Optional[int] = 600
    bemerkung: Optional[str] = None
    hersteller: Optional[str] = None
    modell: Optional[str] = None
    hardware_type_id: Optional[int] = None
    max_watt: Optional[Decimal] = None
    usv_n1_redundant: bool = False


class RackCreate(RackBase):
    pass


class RackUpdate(BaseModel):
    name: Optional[str] = None
    standort: Optional[str] = None
    rackreihe: Optional[str] = None
    hoehe_u: Optional[int] = Field(None, ge=1)
    breite_mm: Optional[int] = 600
    bemerkung: Optional[str] = None
    hersteller: Optional[str] = None
    modell: Optional[str] = None
    hardware_type_id: Optional[int] = None
    max_watt: Optional[Decimal] = None
    usv_n1_redundant: Optional[bool] = None


class Rack(RackBase):
    id: int
    geaendert_von: Optional[str] = None
    geaendert_am: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# === PDU OUTLET SCHEMAS ===
class PduOutletBase(BaseModel):
    pdu_id: int
    outlet_name: str
    phase: Optional[str] = None
    steckdosentyp: Optional[str] = None
    max_watt: Optional[Decimal] = None
    schaltbar: bool = False
    connected_device_id: Optional[int] = None
    connected_port: Optional[str] = None


class PduOutletCreate(PduOutletBase):
    pass


class PduOutletUpdate(BaseModel):
    outlet_name: Optional[str] = None
    phase: Optional[str] = None
    steckdosentyp: Optional[str] = None
    max_watt: Optional[Decimal] = None
    schaltbar: Optional[bool] = None
    connected_device_id: Optional[int] = None
    connected_port: Optional[str] = None


class PduOutlet(PduOutletBase):
    id: int
    pdu_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# === DEVICE DEPENDENCY SCHEMAS ===
class DeviceDependencyBase(BaseModel):
    device_id: int
    depends_on_device_id: int
    dependency_type: Optional[str] = "service"
    dependency_group: Optional[str] = None


class DeviceDependencyCreate(DeviceDependencyBase):
    pass


class DeviceDependency(DeviceDependencyBase):
    model_config = ConfigDict(from_attributes=True)


# === DEVICE SCHEMAS ===
class DeviceBase(BaseModel):
    typ: str
    hostname: str
    ip_adresse: Optional[str] = None
    hersteller: Optional[str] = None
    modell: Optional[str] = None
    seriennummer: Optional[str] = None
    inventarnummer: Optional[str] = None
    rack_id: Optional[int] = None
    u_position: Optional[int] = Field(None, ge=0)
    u_hoehe: int = Field(1, ge=0)
    side: Optional[str] = None
    phase: Optional[str] = None
    tdp_watt: Optional[Decimal] = Field(None, ge=0)
    psu_count: Optional[int] = Field(None, ge=0)
    psu_nennwatt: Optional[Decimal] = Field(None, ge=0)
    last_pct: Optional[Decimal] = Field(Decimal("60.0"), ge=0, le=100)
    anschlussleistung_watt: Optional[Decimal] = Field(None, ge=0)
    einschaltstrom_faktor: Optional[Decimal] = Field(Decimal("2.5"), ge=0)
    shutdown_delay_seconds: Optional[int] = Field(0, ge=0)
    shutdown_priority: Optional[int] = Field(2, ge=1, le=4)
    shutdown_method: Optional[str] = "ACPI_Graceful"
    bemerkung: Optional[str] = None
    strom_typ: Optional[str] = None
    spannung_v: Optional[int] = Field(None, ge=0)
    anschlussleistung_a: Optional[Decimal] = Field(None, ge=0)
    anschluss_stecker: Optional[str] = None


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    typ: Optional[str] = None
    hostname: Optional[str] = None
    ip_adresse: Optional[str] = None
    hersteller: Optional[str] = None
    modell: Optional[str] = None
    seriennummer: Optional[str] = None
    inventarnummer: Optional[str] = None
    rack_id: Optional[int] = None
    u_position: Optional[int] = Field(None, ge=0)
    u_hoehe: Optional[int] = Field(None, ge=0)
    side: Optional[str] = None
    phase: Optional[str] = None
    tdp_watt: Optional[Decimal] = Field(None, ge=0)
    psu_count: Optional[int] = Field(None, ge=0)
    psu_nennwatt: Optional[Decimal] = Field(None, ge=0)
    last_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    anschlussleistung_watt: Optional[Decimal] = Field(None, ge=0)
    einschaltstrom_faktor: Optional[Decimal] = Field(None, ge=0)
    shutdown_delay_seconds: Optional[int] = Field(None, ge=0)
    shutdown_priority: Optional[int] = Field(None, ge=1, le=4)
    shutdown_method: Optional[str] = None
    bemerkung: Optional[str] = None
    strom_typ: Optional[str] = None
    spannung_v: Optional[int] = Field(None, ge=0)
    anschlussleistung_a: Optional[Decimal] = Field(None, ge=0)
    anschluss_stecker: Optional[str] = None


class Device(DeviceBase):
    id: int
    pdu_outlets: List[PduOutlet] = []
    connected_pdu_outlets: List[PduOutlet] = []
    dependencies: List[DeviceDependency] = []
    # Note: interfaces relationship is in the cabling domain
    geaendert_von: Optional[str] = None
    geaendert_am: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# === VIRTUAL MACHINE SCHEMAS ===
class VirtualMachineBase(BaseModel):
    name: str
    host_device_id: Optional[int] = None
    hypervisor_typ: Optional[str] = None
    vm_id_extern: Optional[str] = None
    betriebssystem: Optional[str] = None
    dienst: Optional[str] = None
    ip_adresse: Optional[str] = None
    depends_on_vm_id: Optional[int] = None
    shutdown_priority: Optional[int] = Field(5, ge=1)
    responsible: Optional[str] = None
    bemerkung: Optional[str] = None

class VirtualMachineCreate(VirtualMachineBase):
    pass

class VirtualMachineUpdate(BaseModel):
    name: Optional[str] = None
    host_device_id: Optional[int] = None
    hypervisor_typ: Optional[str] = None
    vm_id_extern: Optional[str] = None
    betriebssystem: Optional[str] = None
    dienst: Optional[str] = None
    ip_adresse: Optional[str] = None
    depends_on_vm_id: Optional[int] = None
    shutdown_priority: Optional[int] = Field(None, ge=1)
    responsible: Optional[str] = None
    bemerkung: Optional[str] = None

class VirtualMachine(VirtualMachineBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

