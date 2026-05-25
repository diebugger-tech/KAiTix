from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.domains.cabling.services import CablingService

router = APIRouter()


@router.get("")
async def search(q: str = "", db: AsyncSession = Depends(get_db)):
    """
    Search across devices, cables, and racks.
    """
    service = CablingService(db)
    return await service.search(q)
