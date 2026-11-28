from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.cabling.kabeltyp_service import KabeltypService
from app.domains.cabling.schemas import Kabeltyp, KabeltypCreate, KabeltypUpdate

router = APIRouter()


@router.get("/", response_model=List[Kabeltyp])
async def list_kabeltypen(
    aktiv: Optional[bool] = None, db: AsyncSession = Depends(get_db)
):
    """Katalog der Kabeltypen. `aktiv=true|false` filtert, ohne Angabe kommen alle."""
    return await KabeltypService(db).list_kabeltypen(aktiv)


@router.post("/", response_model=Kabeltyp, status_code=status.HTTP_201_CREATED)
async def create_kabeltyp(
    kabeltyp_in: KabeltypCreate, db: AsyncSession = Depends(get_db)
):
    return await KabeltypService(db).create_kabeltyp(kabeltyp_in)


@router.put("/{kabeltyp_id}", response_model=Kabeltyp)
async def update_kabeltyp(
    kabeltyp_id: int, kabeltyp_in: KabeltypUpdate, db: AsyncSession = Depends(get_db)
):
    return await KabeltypService(db).update_kabeltyp(kabeltyp_id, kabeltyp_in)


@router.delete("/{kabeltyp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kabeltyp(kabeltyp_id: int, db: AsyncSession = Depends(get_db)):
    await KabeltypService(db).delete_kabeltyp(kabeltyp_id)
    return None
