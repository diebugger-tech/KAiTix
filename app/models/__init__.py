from app.domains.hardware.models import Rack, Device, PduOutlet
from app.domains.cabling.models import Cable, CableStrand, Interface
from app.domains.power.models import UsvUnit, UsvModule, UsvSimulationEvent

# Legacy aliases for unified Interface model
ServerInterface = Interface
DevicePort = Interface

__all__ = [
    "Rack",
    "Device",
    "PduOutlet",
    "Cable",
    "CableStrand",
    "Interface",
    "ServerInterface",
    "DevicePort",
    "UsvUnit",
    "UsvModule",
    "UsvSimulationEvent",
]


