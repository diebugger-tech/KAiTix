from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.deps import get_username
from app.models import Device as DeviceModel, PduOutlet as PduOutletModel
from app.domains.hardware.schemas import (
    Device,
    DeviceCreate,
    DeviceUpdate,
    PduOutlet,
    PduOutletCreate,
    PduOutletUpdate,
)
from pydantic import BaseModel
from app.domains.hardware.routers.devices import (
    _check_side_conflict,
    _check_rack_height_compatibility,
)

router = APIRouter()


def get_pdu_options():
    return [
        selectinload(DeviceModel.pdu_outlets),
        selectinload(DeviceModel.interfaces),
    ]


class PhaseOverview(BaseModel):
    L1: List[PduOutlet] = []
    L2: List[PduOutlet] = []
    L3: List[PduOutlet] = []
    total_outlets: int = 0
    total_max_watt: float = 0


# === PDU CRUD ===


@router.get("/", response_model=List[Device])
async def list_pdus(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DeviceModel).where(DeviceModel.typ == "pdu").options(*get_pdu_options())
    )
    return result.scalars().all()


@router.post("/", response_model=Device, status_code=status.HTTP_201_CREATED)
async def create_pdu(device_in: DeviceCreate, db: AsyncSession = Depends(get_db)):
    data = device_in.model_dump()
    data["typ"] = "pdu"
    if data.get("rack_id"):
        await _check_rack_height_compatibility(
            db, data["rack_id"], data.get("hersteller"), data.get("modell")
        )
    if data.get("u_hoehe") == 0:
        await _check_side_conflict(
            db, data["rack_id"], data.get("side"), exclude_id=None
        )
    db_device = DeviceModel(**data)
    db.add(db_device)
    await db.commit()
    await db.refresh(db_device)
    result = await db.execute(
        select(DeviceModel)
        .where(DeviceModel.id == db_device.id)
        .options(*get_pdu_options())
    )
    return result.scalar_one()


@router.get("/{pdu_id}", response_model=Device)
async def get_pdu(pdu_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DeviceModel)
        .where(DeviceModel.id == pdu_id, DeviceModel.typ == "pdu")
        .options(*get_pdu_options())
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="PDU not found")
    return device


@router.put("/{pdu_id}", response_model=Device)
async def update_pdu(
    pdu_id: int,
    device_in: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    username: str | None = Depends(get_username),
):
    result = await db.execute(
        select(DeviceModel).where(DeviceModel.id == pdu_id, DeviceModel.typ == "pdu")
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="PDU not found")

    update_data = device_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)

    eff_rack = device.rack_id
    if eff_rack:
        await _check_rack_height_compatibility(
            db, eff_rack, device.hersteller, device.modell
        )
    eff_side = update_data.get("side", device.side)
    eff_h_zero = (update_data.get("u_hoehe", device.u_hoehe) or 0) == 0
    if eff_rack and eff_h_zero and eff_side:
        await _check_side_conflict(db, eff_rack, eff_side, exclude_id=pdu_id)

    device.geaendert_von = username
    device.geaendert_am = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(device)
    result = await db.execute(
        select(DeviceModel)
        .where(DeviceModel.id == device.id)
        .options(*get_pdu_options())
    )
    return result.scalar_one()


@router.delete("/{pdu_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pdu(pdu_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DeviceModel).where(DeviceModel.id == pdu_id, DeviceModel.typ == "pdu")
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="PDU not found")
    await db.delete(device)
    await db.commit()
    return None


# === PDU OUTLETS ===


@router.get("/{pdu_id}/outlets", response_model=List[PduOutlet])
async def list_pdu_outlets(pdu_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PduOutletModel)
        .options(selectinload(PduOutletModel.pdu))
        .where(PduOutletModel.pdu_id == pdu_id)
    )
    return result.scalars().all()


@router.post(
    "/{pdu_id}/outlets",
    response_model=PduOutlet,
    status_code=status.HTTP_201_CREATED,
)
async def create_pdu_outlet(
    pdu_id: int, outlet_in: PduOutletCreate, db: AsyncSession = Depends(get_db)
):
    # Verify PDU exists
    pdu = await db.execute(
        select(DeviceModel).where(DeviceModel.id == pdu_id, DeviceModel.typ == "pdu")
    )
    pdu_obj = pdu.scalar_one_or_none()
    if not pdu_obj:
        raise HTTPException(status_code=404, detail="PDU not found")

    data = outlet_in.model_dump()
    data["pdu_id"] = pdu_id
    db_outlet = PduOutletModel(**data)
    db.add(db_outlet)
    await db.commit()
    await db.refresh(db_outlet)

    # Pre-populate the relationship to avoid MissingGreenlet on Pydantic serialization
    db_outlet.pdu = pdu_obj

    return db_outlet


@router.put("/{pdu_id}/outlets/{outlet_id}", response_model=PduOutlet)
async def update_pdu_outlet(
    pdu_id: int,
    outlet_id: int,
    outlet_in: PduOutletUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PduOutletModel)
        .options(selectinload(PduOutletModel.pdu))
        .where(PduOutletModel.id == outlet_id, PduOutletModel.pdu_id == pdu_id)
    )
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="PDU outlet not found")

    update_data = outlet_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(outlet, field, value)

    await db.commit()
    await db.refresh(outlet)
    return outlet


@router.delete("/{pdu_id}/outlets/{outlet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pdu_outlet(
    pdu_id: int, outlet_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(PduOutletModel).where(
            PduOutletModel.id == outlet_id, PduOutletModel.pdu_id == pdu_id
        )
    )
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="PDU outlet not found")
    await db.delete(outlet)
    await db.commit()
    return None


# === PHASE OVERVIEW ===


@router.get("/{pdu_id}/phase-overview", response_model=PhaseOverview)
async def get_pdu_phase_overview(pdu_id: int, db: AsyncSession = Depends(get_db)):
    # Verify PDU exists
    pdu = await db.execute(
        select(DeviceModel).where(DeviceModel.id == pdu_id, DeviceModel.typ == "pdu")
    )
    if not pdu.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="PDU not found")

    result = await db.execute(
        select(PduOutletModel)
        .options(selectinload(PduOutletModel.pdu))
        .where(PduOutletModel.pdu_id == pdu_id)
    )
    outlets = result.scalars().all()

    phase_map: dict[str, list] = {"L1": [], "L2": [], "L3": []}
    total_watt = 0.0

    for outlet in outlets:
        phase_key = outlet.phase or "L1"
        if phase_key in phase_map:
            phase_map[phase_key].append(outlet)
        if outlet.max_watt:
            total_watt += float(outlet.max_watt)

    return PhaseOverview(
        L1=phase_map["L1"],
        L2=phase_map["L2"],
        L3=phase_map["L3"],
        total_outlets=len(outlets),
        total_max_watt=total_watt,
    )
