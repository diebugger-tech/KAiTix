from app.domains.hardware.models import Rack, Device, PduOutlet
from app.domains.cabling.models import Cable, CableStrand, Interface, Kabeltyp
from app.domains.power.models import UsvUnit, UsvModule, UsvSimulationEvent
from app.domains.hardware.models import VirtualMachine
from app.domains.runbooks.models import (
    Runbook,
    RunbookLayer,
    RunbookDevice,
    RunbookExecution,
    RunbookExecutionStep,
)
from app.domains.network.models import Vlan, Subnet
from app.domains.umbau.models import (
    Umbau,
    UmbauRack,
    UmbauGeraetepruefung,
    UmbauEnde,
    UmbauEreignis,
)

# Legacy aliases for unified Interface model
DevicePort = Interface

__all__ = [
    "Rack",
    "Device",
    "PduOutlet",
    "Cable",
    "Kabeltyp",
    "CableStrand",
    "Interface",
    "DevicePort",
    "UsvUnit",
    "UsvModule",
    "UsvSimulationEvent",
    "VirtualMachine",
    "Runbook",
    "RunbookLayer",
    "RunbookDevice",
    "RunbookExecution",
    "RunbookExecutionStep",
    "Vlan",
    "Subnet",
    "Umbau",
    "UmbauRack",
    "UmbauGeraetepruefung",
    "UmbauEnde",
    "UmbauEreignis",
]
