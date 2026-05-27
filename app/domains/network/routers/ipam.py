from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.domains.network.models import Vlan, Subnet
from app.domains.network.schemas import VlanResponse, SubnetResponse

router = APIRouter(prefix="/ipam", tags=["IPAM"])


@router.get("/vlans", response_model=List[VlanResponse])
async def get_vlans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vlan).order_by(Vlan.vlan_id))
    return result.scalars().all()


@router.get("/subnets", response_model=List[SubnetResponse])
async def get_subnets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subnet).order_by(Subnet.id))
    return result.scalars().all()
