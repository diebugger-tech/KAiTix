from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import Device as DeviceModel
from app.domains.power.services.phase_optimizer import optimize_phases
from app.domains.power.services.usv_calc import PhaseBalancer

router = APIRouter()


class EmpfehlungBase(BaseModel):
    device_id: int
    neue_phase: str


@router.post("/optimize/{rack_id}")
async def optimize_rack_phases(rack_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DeviceModel).where(
            DeviceModel.rack_id == rack_id,
            DeviceModel.tdp_watt.is_not(None),
            DeviceModel.phase.is_not(None),
        )
    )
    devices = result.scalars().all()

    if not devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No suitable devices found in rack {rack_id}",
        )

    return optimize_phases(devices)  # type: ignore


@router.post("/optimize/{rack_id}/apply")
async def apply_rack_phases(
    rack_id: int,
    recommendations: List[EmpfehlungBase],
    db: AsyncSession = Depends(get_db),
):
    # 1. Apply the new phases
    updated_count = 0
    for req in recommendations:
        result = await db.execute(
            select(DeviceModel).where(
                DeviceModel.id == req.device_id, DeviceModel.rack_id == rack_id
            )
        )
        device = result.scalar_one_or_none()
        if device:
            device.phase = req.neue_phase
            updated_count += 1

    await db.commit()

    # 2. Recalculate imbalance
    result = await db.execute(
        select(DeviceModel).where(
            DeviceModel.rack_id == rack_id,
            DeviceModel.tdp_watt.is_not(None),
            DeviceModel.phase.is_not(None),
        )
    )
    devices = result.scalars().all()

    neue_imbalance_pct = 0.0
    if devices:
        balance_result = PhaseBalancer.calculate_balancing(devices)  # type: ignore
        neue_imbalance_pct = balance_result.get(
            "initial_imbalance_pct", 0.0
        )  # initial is the current since we don't optimize here

    return {
        "status": "ok",
        "updated": updated_count,
        "neue_imbalance_pct": neue_imbalance_pct,
    }
