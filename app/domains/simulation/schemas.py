from typing import List, Optional
from pydantic import BaseModel

class SimulationScenario(BaseModel):
    target_type: str  # "phase", "usv_module", "device", "pdu_outlet", "network_switch"
    target_id: Optional[int] = None
    target_name: Optional[str] = None

class AffectedDevice(BaseModel):
    device_id: int
    state: str  # "red" (off), "yellow" (redundant power lost), "green" (ok)
    reasons: List[str]

class AffectedVM(BaseModel):
    vm_id: int
    state: str  # "red" (off), "yellow" (degraded)
    reasons: List[str]

class AffectedRunbook(BaseModel):
    runbook_id: int
    reasons: List[str]

class TimelineEvent(BaseModel):
    time_seconds: int
    device_id: int
    action: str  # "shutdown" or "boot"
    method: str  # e.g., "ACPI_Graceful", "Hard_Power_Cut"
    warning: bool = False
    message: str

class SimulationResult(BaseModel):
    affected_devices: List[AffectedDevice]
    affected_vms: List[AffectedVM] = []
    affected_runbooks: List[AffectedRunbook] = []
    shutdown_timeline: List[TimelineEvent]
    boot_timeline: List[TimelineEvent]
    usv_battery_warning: bool = False
    messages: List[str] = []
