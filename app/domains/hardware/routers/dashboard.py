from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models import Device

router = APIRouter()


@router.get("/health")
async def get_health():
    return {"status": "healthy", "message": "System online"}


@router.get("/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device.tdp_watt))
    tdp_watts = result.scalars().all()

    total_tdp_watt = sum(float(w or 0) for w in tdp_watts)
    total_power_kw = total_tdp_watt / 1000.0

    return {"total_power_kw": total_power_kw}
