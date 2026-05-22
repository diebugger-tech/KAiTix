from app.domains.hardware.schemas import (
    Rack,
    RackCreate,
    RackUpdate,
    Device,
    DeviceCreate,
    DeviceUpdate,
    PduOutlet,
    PduOutletCreate,
    PduOutletUpdate,
)
from app.domains.cabling.schemas import (
    Cable,
    CableCreate,
    CableUpdate,
    CableStrand,
    CableStrandCreate,
    CableStrandUpdate,
    Interface,
    InterfaceCreate,
    InterfaceUpdate,
    InterfaceBody,
)

from app.domains.power.schemas import (
    UsvUnit,
    UsvUnitCreate,
    UsvUnitUpdate,
    UsvModule,
    UsvModuleCreate,
    UsvModuleUpdate,
    UsvSimulationEventResponse,
)


# Legacy aliases for unified Interface schemas
ServerInterface = Interface
ServerInterfaceCreate = InterfaceCreate
ServerInterfaceUpdate = InterfaceUpdate
ServerInterfaceBody = InterfaceCreate # Fallback

DevicePort = Interface
DevicePortCreate = InterfaceCreate
DevicePortUpdate = InterfaceUpdate

__all__ = [
    "Rack",
    "RackCreate",
    "RackUpdate",
    "Device",
    "DeviceCreate",
    "DeviceUpdate",
    "PduOutlet",
    "PduOutletCreate",
    "PduOutletUpdate",
    "Cable",
    "CableCreate",
    "CableUpdate",
    "CableStrand",
    "CableStrandCreate",
    "CableStrandUpdate",
    "Interface",
    "InterfaceCreate",
    "InterfaceUpdate",
    "InterfaceBody",

    "ServerInterface",
    "ServerInterfaceCreate",
    "ServerInterfaceUpdate",
    "ServerInterfaceBody",
    "DevicePort",
    "DevicePortCreate",
    "DevicePortUpdate",
    "UsvUnit",
    "UsvUnitCreate",
    "UsvUnitUpdate",
    "UsvModule",
    "UsvModuleCreate",
    "UsvModuleUpdate",
    "UsvSimulationEventResponse",
]

