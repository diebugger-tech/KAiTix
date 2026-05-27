from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.domains.hardware.schemas import Device, VirtualMachine


# === RUNBOOK EXECUTION STEP SCHEMAS ===
class RunbookExecutionStepBase(BaseModel):
    runbook_device_id: int
    note: Optional[str] = None


class RunbookExecutionStepCreate(RunbookExecutionStepBase):
    pass


class RunbookExecutionStep(RunbookExecutionStepBase):
    id: int
    execution_id: int
    abgehakt_am: Optional[datetime] = None
    abgehakt_von: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class RunbookExecutionStepCheckRequest(BaseModel):
    note: Optional[str] = None


# === RUNBOOK EXECUTION SCHEMAS ===
class RunbookExecutionBase(BaseModel):
    runbook_id: int
    modus: str


class RunbookExecutionCreate(RunbookExecutionBase):
    pass


class RunbookExecution(RunbookExecutionBase):
    id: int
    gestartet_am: datetime
    gestartet_von: Optional[str] = None
    status: str
    note: Optional[str] = None
    steps: List[RunbookExecutionStep] = []
    model_config = ConfigDict(from_attributes=True)


class RunbookExecutionStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


# === RUNBOOK DEVICE SCHEMAS ===
class RunbookDeviceBase(BaseModel):
    device_id: Optional[int] = None
    vm_id: Optional[int] = None
    freitext: Optional[str] = None
    delay_seconds: int = 30
    responsible: Optional[str] = None
    note: Optional[str] = None
    position: int = 1


class RunbookDeviceCreate(RunbookDeviceBase):
    layer_id: int


class RunbookDeviceUpdate(BaseModel):
    layer_id: Optional[int] = None
    delay_seconds: Optional[int] = None
    responsible: Optional[str] = None
    note: Optional[str] = None
    position: Optional[int] = None


class RunbookDevice(RunbookDeviceBase):
    id: int
    runbook_id: int
    layer_id: int
    # We use ForwardRef or Optional[Any] if Circular import occurs.
    # Fortunately, we already imported Device and VirtualMachine schemas.
    # However, to avoid heavy nesting issues, we can just return standard dict representations or use them directly.
    # Note: Using Optional[Any] here avoids schema validation recursion loops if not careful.
    # We will use the actual models, but if it causes issues we can fall back to dicts.
    # Actually, Device schema might be heavy. Let's create a minimal schema for reference.

    device: Optional[Device] = None
    vm: Optional[VirtualMachine] = None
    model_config = ConfigDict(from_attributes=True)


class RunbookDeviceReorderRequest(BaseModel):
    device_ids: List[int]


# === RUNBOOK LAYER SCHEMAS ===
class RunbookLayerBase(BaseModel):
    name: str
    position: int = 1
    markdown_note: Optional[str] = None
    shutdown_order: Optional[int] = None
    startup_order: Optional[int] = None


class RunbookLayerCreate(RunbookLayerBase):
    pass


class RunbookLayerUpdate(BaseModel):
    name: Optional[str] = None
    markdown_note: Optional[str] = None


class RunbookLayer(RunbookLayerBase):
    id: int
    runbook_id: int
    devices: List[RunbookDevice] = []
    model_config = ConfigDict(from_attributes=True)


class RunbookLayerReorderRequest(BaseModel):
    layer_ids: List[int]


# === RUNBOOK SCHEMAS ===
class RunbookBase(BaseModel):
    name: str
    typ: str
    beschreibung: Optional[str] = None


class RunbookCreate(RunbookBase):
    pass


class RunbookUpdate(BaseModel):
    name: Optional[str] = None
    typ: Optional[str] = None
    beschreibung: Optional[str] = None


class Runbook(RunbookBase):
    id: int
    erstellt_am: datetime
    erstellt_von: Optional[str] = None
    generated_from_id: Optional[int] = None
    layers: List[RunbookLayer] = []
    model_config = ConfigDict(from_attributes=True)
