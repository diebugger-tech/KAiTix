from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.api.deps import get_username

from app.models import Device as DeviceModel, Rack as RackModel, PduOutlet
from app.schemas import (
    Device,
    DeviceCreate,
    DeviceUpdate,
    InterfaceBody,
)

router = APIRouter()


async def _check_u_conflict(
    db: AsyncSession,
    rack_id: int,
    u_position: int,
    u_hoehe: int,
    exclude_id: int | None = None,
) -> None:
    """Raises HTTP 409 if the given U-range overlaps with any existing device in the rack."""
    if u_hoehe == 0:
        return  # 0U PDUs are side-mounted, no conflict possible
    result = await db.execute(
        select(DeviceModel).where(
            DeviceModel.rack_id == rack_id,
            DeviceModel.u_position.isnot(None),
            DeviceModel.u_hoehe > 0,
        )
    )
    occupants = result.scalars().all()
    for dev in occupants:
        if exclude_id and dev.id == exclude_id:
            continue
        # Overlap: ranges [a, a+h) and [b, b+h) overlap when a < b+h AND b < a+h
        a, ah = u_position, u_hoehe
        b, bh = dev.u_position, dev.u_hoehe
        if a < b + bh and b < a + ah:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"U-Positions-Konflikt: HE {a}–{a + ah - 1} überschneidet sich mit "
                    f"'{dev.hostname}' (HE {b}–{b + bh - 1})"
                ),
            )


async def _check_rack_height_compatibility(
    db: AsyncSession,
    rack_id: int | None,
    hersteller: str | None,
    modell: str | None,
) -> None:
    """Raises HTTP 400 if the device's hardware catalog template requires a min_rack_hoehe greater than the rack's hoehe_u."""
    if not rack_id or not hersteller or not modell:
        return

    from app.domains.hardware.routers.hardware import _load_hardware

    hardware_types = _load_hardware()
    matching_hw = None
    for hw in hardware_types:
        if hw.get("hersteller") == hersteller and hw.get("modell") == modell:
            matching_hw = hw
            break

    if matching_hw and matching_hw.get("min_rack_hoehe", 0) > 0:
        result = await db.execute(select(RackModel).where(RackModel.id == rack_id))
        rack = result.scalar_one_or_none()
        if rack and rack.hoehe_u < matching_hw["min_rack_hoehe"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Kompatibilitätsfehler: Das Gerät '{hersteller} {modell}' "
                    f"benötigt ein Rack mit mindestens {matching_hw['min_rack_hoehe']} HE. "
                    f"Rack '{rack.name}' hat nur {rack.hoehe_u} HE."
                ),
            )


async def _check_side_conflict(
    db: AsyncSession,
    rack_id: int,
    side: str | None,
    exclude_id: int | None = None,
) -> None:
    """Raises HTTP 400 if the given 0U side is already occupied in the rack."""
    if not side or not rack_id:
        return
    result = await db.execute(
        select(DeviceModel).where(
            DeviceModel.rack_id == rack_id,
            DeviceModel.u_hoehe == 0,
            DeviceModel.side == side,
        )
    )
    occupant = result.scalar_one_or_none()
    if occupant and (exclude_id is None or occupant.id != exclude_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Seitenkonflikt: Seite {side} ist bereits mit "
                f"'{occupant.hostname}' belegt. "
                f"Pro Seite ist nur eine vertikale PDU möglich."
            ),
        )


def get_device_options():
    # interfaces table does not exist yet (pending Phase-1 migration)
    return [
        selectinload(DeviceModel.pdu_outlets),
        selectinload(DeviceModel.connected_pdu_outlets),
    ]


@router.get("/types")
async def list_device_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DeviceModel.typ).distinct().order_by(DeviceModel.typ)
    )
    types = [row[0] for row in result.all()]
    has_power = (await db.execute(select(PduOutlet).limit(1))).first() is not None
    return {"device_types": types, "has_power_edges": has_power}


@router.get("/", response_model=List[Device])
async def list_devices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DeviceModel).options(*get_device_options()))
    return result.scalars().all()


@router.post("/", response_model=Device, status_code=status.HTTP_201_CREATED)
async def create_device(device_in: DeviceCreate, db: AsyncSession = Depends(get_db)):
    data = device_in.model_dump()
    if data.get("rack_id") and data.get("u_position") is not None:
        await _check_u_conflict(
            db, data["rack_id"], data["u_position"], data.get("u_hoehe") or 1
        )
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
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database integrity violation: {str(e.orig) if hasattr(e, 'orig') else str(e)}",
        )
    await db.refresh(db_device)
    # Reload with all relations
    result = await db.execute(
        select(DeviceModel)
        .where(DeviceModel.id == db_device.id)
        .options(*get_device_options())
    )
    return result.scalar_one()


@router.get("/{device_id}", response_model=Device)
async def get_device(device_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DeviceModel)
        .where(DeviceModel.id == device_id)
        .options(*get_device_options())
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.put("/{device_id}", response_model=Device)
async def update_device(
    device_id: int,
    device_in: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    username: str | None = Depends(get_username),
):
    result = await db.execute(select(DeviceModel).where(DeviceModel.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    update_data = device_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)

    # Conflict check with merged state
    eff_rack = device.rack_id
    eff_pos = device.u_position
    eff_h = device.u_hoehe or 1
    if eff_rack and eff_pos is not None:
        await _check_u_conflict(db, eff_rack, eff_pos, eff_h, exclude_id=device_id)

    if eff_rack:
        await _check_rack_height_compatibility(
            db, eff_rack, device.hersteller, device.modell
        )
    eff_side = update_data.get("side", device.side)
    eff_h_zero = (update_data.get("u_hoehe", device.u_hoehe) or 0) == 0
    if eff_rack and eff_h_zero and eff_side:
        await _check_side_conflict(db, eff_rack, eff_side, exclude_id=device_id)

    device.geaendert_von = username
    device.geaendert_am = datetime.now(timezone.utc)

    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database integrity violation: {str(e.orig) if hasattr(e, 'orig') else str(e)}",
        )
    await db.refresh(device)
    # Reload with relations
    result = await db.execute(
        select(DeviceModel)
        .where(DeviceModel.id == device.id)
        .options(*get_device_options())
    )
    return result.scalar_one()


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DeviceModel).where(DeviceModel.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    await db.delete(device)
    await db.commit()
    return None


@router.post("/{device_id}/interfaces", status_code=201)
async def add_interface(
    device_id: int, data: InterfaceBody, db: AsyncSession = Depends(get_db)
):
    from app.models import Interface

    iface = Interface(
        device_id=device_id,
        port_name=data.port_name,
        typ=data.typ,
        mac_adresse=data.mac_adresse,
        switch_hostname=data.switch_hostname,
        switch_port=data.switch_port,
    )
    db.add(iface)
    await db.commit()
    await db.refresh(iface)
    return {"id": iface.id, "port_name": iface.port_name, "typ": iface.typ}
