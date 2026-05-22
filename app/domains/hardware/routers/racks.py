from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.models import Rack as RackModel
from app.schemas import Rack, RackCreate, RackUpdate
from app.api.deps import get_username

router = APIRouter()


@router.get("/", response_model=List[Rack])
async def list_racks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RackModel).options(selectinload(RackModel.devices))
    )
    return result.scalars().all()


@router.post("/", response_model=Rack, status_code=status.HTTP_201_CREATED)
async def create_rack(rack_in: RackCreate, db: AsyncSession = Depends(get_db)):
    try:
        db_rack = RackModel(**rack_in.model_dump())
        db.add(db_rack)
        await db.commit()
        await db.refresh(db_rack)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ein Rack mit diesem Namen existiert bereits",
        )
    # Reload with devices
    result = await db.execute(
        select(RackModel)
        .where(RackModel.id == db_rack.id)
        .options(selectinload(RackModel.devices))
    )
    return result.scalar_one()


@router.get("/{rack_id}", response_model=Rack)
async def get_rack(rack_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RackModel)
        .where(RackModel.id == rack_id)
        .options(selectinload(RackModel.devices))
    )
    rack = result.scalar_one_or_none()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")
    return rack


@router.put("/{rack_id}", response_model=Rack)
async def update_rack(
    rack_id: int,
    rack_in: RackUpdate,
    db: AsyncSession = Depends(get_db),
    username: str | None = Depends(get_username),
):
    result = await db.execute(select(RackModel).where(RackModel.id == rack_id))
    rack = result.scalar_one_or_none()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")

    update_data = rack_in.model_dump(exclude_unset=True)
    if "hoehe_u" in update_data:
        new_hoehe_u = update_data["hoehe_u"]
        from app.models import Device as DeviceModel

        res = await db.execute(
            select(DeviceModel).where(DeviceModel.rack_id == rack_id)
        )
        devices = res.scalars().all()

        from app.domains.hardware.routers.hardware import _load_hardware

        hardware_types = _load_hardware()

        for dev in devices:
            if dev.hersteller and dev.modell:
                matching_hw = None
                for hw in hardware_types:
                    if (
                        hw.get("hersteller") == dev.hersteller
                        and hw.get("modell") == dev.modell
                    ):
                        matching_hw = hw
                        break
                if matching_hw and matching_hw.get("min_rack_hoehe", 0) > new_hoehe_u:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Höhenkonflikt: Rack-Höhe kann nicht auf {new_hoehe_u} HE reduziert werden, "
                            f"da das eingebaute Gerät '{dev.hostname}' ({dev.hersteller} {dev.modell}) "
                            f"mindestens {matching_hw['min_rack_hoehe']} HE benötigt."
                        ),
                    )

    try:
        for field, value in update_data.items():
            setattr(rack, field, value)
        rack.geaendert_von = username
        rack.geaendert_am = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(rack)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ein Rack mit diesem Namen existiert bereits",
        )
    # Reload with devices
    result = await db.execute(
        select(RackModel)
        .where(RackModel.id == rack.id)
        .options(selectinload(RackModel.devices))
    )
    return result.scalar_one()


@router.delete("/{rack_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rack(rack_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RackModel).where(RackModel.id == rack_id))
    rack = result.scalar_one_or_none()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")
    try:
        await db.delete(rack)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dieses Rack kann nicht gelöscht werden, da noch Geräte oder Verbindungen darauf verweisen",
        )
    return None
