from fastapi import APIRouter
from app.domains.hardware.routers import racks, devices, hardware, pdus
from app.domains.cabling.routers import cables, topology, search
from app.domains.power.routers import usv
from app.domains.import_export.routers import (
    import_csv,
    import_eplan,
    export,
    rack_export,
    topology_pdf,
)

api_router = APIRouter()

api_router.include_router(racks.router, prefix="/racks", tags=["racks"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(cables.router, prefix="/cables", tags=["cables"])
api_router.include_router(usv.router, prefix="/usv", tags=["usv"])
api_router.include_router(
    import_eplan.router, prefix="/import-eplan", tags=["import-eplan"]
)
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(pdus.router, prefix="/pdus", tags=["pdus"])
api_router.include_router(hardware.router, prefix="/hardware", tags=["hardware"])
api_router.include_router(rack_export.router, prefix="", tags=["pdf-export"])
api_router.include_router(import_csv.router, prefix="/import-csv", tags=["import-csv"])
api_router.include_router(topology.router, prefix="/topology", tags=["topology"])
api_router.include_router(topology_pdf.router, prefix="/topology", tags=["topology"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
