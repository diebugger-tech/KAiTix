from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_username
from app.domains.cabling.schemas import Cable, CableCreate, CableUpdate
from app.domains.cabling.services import CablingService

router = APIRouter()


@router.get("/legend", response_model=Dict[str, Any])
async def get_cable_color_legend():
    """
    Returns the standardized data center cable color coding legend.
    """
    return CablingService.CABLE_COLOR_LEGEND


@router.get("/suggest-color")
async def suggest_cable_color(typ: str):
    """
    Suggests a default cable color based on the cable type.
    """
    return CablingService.suggest_color(typ)


@router.get("/color-rules", response_model=Dict[str, Any])
async def get_color_rules():
    """
    Returns the project-specific cable color rules from JSON storage.
    """
    return CablingService.load_color_rules()


@router.put("/color-rules", response_model=Dict[str, Any])
async def update_color_rules(rules_payload: Dict[str, Any]):
    """
    Updates the cable color rules JSON file.
    """
    return CablingService.update_color_rules(rules_payload)


@router.get("/", response_model=List[Cable])
async def list_cables(db: AsyncSession = Depends(get_db)):
    service = CablingService(db)
    return await service.list_cables()


@router.post("/", response_model=Cable, status_code=status.HTTP_201_CREATED)
async def create_cable(cable_in: CableCreate, db: AsyncSession = Depends(get_db)):
    service = CablingService(db)
    return await service.create_cable(cable_in)


@router.get("/{cable_id}", response_model=Cable)
async def get_cable(cable_id: int, db: AsyncSession = Depends(get_db)):
    service = CablingService(db)
    return await service.get_cable(cable_id)


@router.put("/{cable_id}", response_model=Cable)
async def update_cable(
    cable_id: int,
    cable_in: CableUpdate,
    db: AsyncSession = Depends(get_db),
    username: str | None = Depends(get_username),
):
    service = CablingService(db)
    return await service.update_cable(cable_id, cable_in, username)


@router.delete("/{cable_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cable(cable_id: int, db: AsyncSession = Depends(get_db)):
    service = CablingService(db)
    await service.delete_cable(cable_id)
    return None


@router.get("/{cable_id}/trace")
async def trace_cable(cable_id: int, db: AsyncSession = Depends(get_db)):
    service = CablingService(db)
    return await service.trace_cable(cable_id)
