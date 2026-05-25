from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from app.domains.hardware.models import Device as DeviceModel
import json
from app.core.database import get_db
from app.models import (
    UsvUnit as UsvUnitModel,
    UsvModule as UsvModuleModel,
    UsvSimulationEvent,
)
from app.schemas import (
    UsvUnit,
    UsvUnitCreate,
    UsvModule,
    UsvModuleCreate,
    UsvModuleUpdate,
    UsvSimulationEventResponse,
)
from app.domains.power.services.usv_calc import (
    UsvCalculator,
    FaultSimulationEngine,
    BatteryCabinetEngine,
    ShutdownSimulationEngine,
)

router = APIRouter()


class UsvSimulationRequest(BaseModel):
    l1_kw: Decimal = Field(..., ge=0, description="Phase L1 load in kW")
    l2_kw: Decimal = Field(..., ge=0, description="Phase L2 load in kW")
    l3_kw: Decimal = Field(..., ge=0, description="Phase L3 load in kW")
    module_capacity_kw: Decimal = Field(
        Decimal("10.0"), gt=0, description="UPS module capacity in kW"
    )
    installed_modules_count: int = Field(
        ..., ge=0, description="Number of installed modules"
    )


class SimulateFaultRequest(BaseModel):
    fault_type: str
    l1_kw: Decimal = Field(..., ge=0)
    l2_kw: Decimal = Field(..., ge=0)
    l3_kw: Decimal = Field(..., ge=0)
    module_capacity_kw: Decimal = Field(Decimal("10.0"), gt=0)
    installed_modules_count: int = Field(..., ge=0)
    system_state: Optional[Dict[str, Any]] = None
    battery_voltage: Decimal = Field(Decimal("48"), gt=0)
    battery_capacity_ah: Decimal = Field(Decimal("100"), gt=0)
    peukert_exponent: Decimal = Field(Decimal("1.2"), gt=0)
    inverter_efficiency: Decimal = Field(Decimal("0.90"), gt=0, le=1)


# === USV UNITS ===


@router.get("/", response_model=List[UsvUnit])
async def list_usv_units(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UsvUnitModel).options(selectinload(UsvUnitModel.modules))
    )
    return result.scalars().all()


@router.post("/", response_model=UsvUnit, status_code=status.HTTP_201_CREATED)
async def create_usv_unit(usv_in: UsvUnitCreate, db: AsyncSession = Depends(get_db)):
    db_usv = UsvUnitModel(**usv_in.model_dump())
    db.add(db_usv)
    await db.commit()
    await db.refresh(db_usv)
    result = await db.execute(
        select(UsvUnitModel)
        .where(UsvUnitModel.id == db_usv.id)
        .options(selectinload(UsvUnitModel.modules))
    )
    return result.scalar_one()


@router.get("/events", response_model=List[UsvSimulationEventResponse])
async def list_simulation_events(
    limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db)
):
    """Returns the most recent simulation events."""
    result = await db.execute(
        select(UsvSimulationEvent)
        .order_by(UsvSimulationEvent.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{usv_unit_id}", response_model=UsvUnit)
async def get_usv_unit(usv_unit_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UsvUnitModel)
        .where(UsvUnitModel.id == usv_unit_id)
        .options(selectinload(UsvUnitModel.modules))
    )
    usv = result.scalar_one_or_none()
    if not usv:
        raise HTTPException(status_code=404, detail="USV unit not found")
    return usv


# === USV MODULES ===


@router.post(
    "/{usv_unit_id}/modules",
    response_model=UsvModule,
    status_code=status.HTTP_201_CREATED,
)
async def create_usv_module(
    usv_unit_id: int, module_in: UsvModuleCreate, db: AsyncSession = Depends(get_db)
):
    # Check USV exists
    result = await db.execute(
        select(UsvUnitModel).where(UsvUnitModel.id == usv_unit_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="USV unit not found")

    db_module = UsvModuleModel(**module_in.model_dump())
    db_module.usv_unit_id = usv_unit_id
    db.add(db_module)
    await db.commit()
    await db.refresh(db_module)
    return db_module


@router.put("/modules/{module_id}", response_model=UsvModule)
async def update_usv_module(
    module_id: int, module_in: UsvModuleUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UsvModuleModel).where(UsvModuleModel.id == module_id)
    )
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="USV module not found")

    update_data = module_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(module, field, value)

    await db.commit()
    await db.refresh(module)
    return module


# === CALCULATIONS & SIMULATIONS ===


@router.get("/{usv_unit_id}/status")
async def get_usv_status(usv_unit_id: int, db: AsyncSession = Depends(get_db)):
    """
    Computes active/peak 3-phase electrical loads and N+1 status for the specified UPS unit.
    """
    res = await UsvCalculator.get_usv_load_and_status(usv_unit_id, db)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/simulate")
def simulate_usv(sim_req: UsvSimulationRequest):
    """
    Runs a sandbox simulation of 3-phase loads on a hypothetical UPS setup.
    """
    return UsvCalculator.simulate_sandbox_usv(
        l1_kw=sim_req.l1_kw,
        l2_kw=sim_req.l2_kw,
        l3_kw=sim_req.l3_kw,
        module_capacity_kw=sim_req.module_capacity_kw,
        installed_modules_count=sim_req.installed_modules_count,
    )


# === FAULT SIMULATION ===


@router.post("/simulate/fault")
async def simulate_fault(
    sim_req: SimulateFaultRequest, db: AsyncSession = Depends(get_db)
):
    """
    Inject a fault into the UPS simulation and return updated system state.
    Supported fault types: reset, grid_failure, battery_defect, module_failure.
    Events are persisted to the database.
    """
    result = FaultSimulationEngine.simulate_fault(
        fault_type=sim_req.fault_type,
        l1_kw=sim_req.l1_kw,
        l2_kw=sim_req.l2_kw,
        l3_kw=sim_req.l3_kw,
        module_capacity_kw=sim_req.module_capacity_kw,
        installed_modules_count=sim_req.installed_modules_count,
        system_state=sim_req.system_state,
        battery_voltage=sim_req.battery_voltage,
        battery_capacity_ah=sim_req.battery_capacity_ah,
        peukert_exponent=sim_req.peukert_exponent,
        inverter_efficiency=sim_req.inverter_efficiency,
    )

    event_data = result["event"]
    snapshot = json.dumps(result["system_state"], default=str)

    db_event = UsvSimulationEvent(
        timestamp=datetime.now(timezone.utc),
        event_type=event_data["event_type"],
        severity=event_data["severity"],
        description=event_data["description"],
        snapshot_json=snapshot,
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)

    return {
        "system_state": result["system_state"],
        "event": UsvSimulationEventResponse.model_validate(db_event),
    }


# === BATTERY CABINET CALCULATIONS ===


class RuntimeCurveRequest(BaseModel):
    l1_kw: Decimal = Field(..., ge=0)
    l2_kw: Decimal = Field(..., ge=0)
    l3_kw: Decimal = Field(..., ge=0)
    module_capacity_kw: Decimal = Field(Decimal("10.0"), gt=0)
    installed_modules_count: int = Field(..., ge=0)
    battery_type: str = "vrla"
    series_blocks: int = Field(4, gt=0)
    parallel_strings: int = Field(1, gt=0)
    block_voltage_v: Decimal = Field(Decimal("12"), gt=0)
    block_capacity_ah: Decimal = Field(Decimal("100"), gt=0)
    age_years: Decimal = Field(Decimal("0"), ge=0)
    temperature_c: Decimal = Field(Decimal("20"), ge=-273.15)
    inverter_efficiency: Decimal = Field(Decimal("0.90"), gt=0, le=1)


class DimensioningRequest(BaseModel):
    load_kw: Decimal = Field(..., ge=0)
    target_runtime_min: Decimal = Field(..., gt=0)
    battery_type: str = "vrla"
    block_voltage_v: Decimal = Field(Decimal("12"), gt=0)
    block_capacity_ah: Decimal = Field(Decimal("100"), gt=0)
    inverter_efficiency: Decimal = Field(Decimal("0.90"), gt=0, le=1)
    system_voltage_v: Decimal = Field(Decimal("48"), gt=0)
    safety_margin_pct: Decimal = Field(Decimal("0.15"), ge=0, le=1)


@router.post("/battery/runtime-curve")
def get_runtime_curve(req: RuntimeCurveRequest):
    """Returns Peukert-based runtime vs load curve for the given battery configuration."""
    return BatteryCabinetEngine.calculate_runtime_curve(
        l1_kw=req.l1_kw,
        l2_kw=req.l2_kw,
        l3_kw=req.l3_kw,
        module_capacity_kw=req.module_capacity_kw,
        installed_modules_count=req.installed_modules_count,
        battery_type=req.battery_type,
        series_blocks=req.series_blocks,
        parallel_strings=req.parallel_strings,
        block_voltage_v=req.block_voltage_v,
        block_capacity_ah=req.block_capacity_ah,
        age_years=req.age_years,
        temperature_c=req.temperature_c,
        inverter_efficiency=req.inverter_efficiency,
    )


@router.post("/battery/dimension")
def get_battery_dimensioning(req: DimensioningRequest):
    """Reverse calculation: how many battery blocks for X minutes at Y kW load."""
    return BatteryCabinetEngine.calculate_dimensioning(
        load_kw=req.load_kw,
        target_runtime_min=req.target_runtime_min,
        battery_type=req.battery_type,
        block_voltage_v=req.block_voltage_v,
        block_capacity_ah=req.block_capacity_ah,
        inverter_efficiency=req.inverter_efficiency,
        system_voltage_v=req.system_voltage_v,
        safety_margin_pct=req.safety_margin_pct,
    )


# === SHUTDOWN SIMULATION ===


class ShutdownTimelinePoint(BaseModel):
    time_seconds: int
    soc_pct: float
    load_kw: float
    remaining_runtime_min: float
    active_device_ids: List[int]


class ShutdownDeviceStatus(BaseModel):
    id: int
    hostname: str
    tdp_watt: float
    shutdown_delay_seconds: int
    shutdown_priority: int
    crashed: bool
    crash_reason: Optional[str] = None
    shutdown_at_seconds: Optional[int] = None


class ShutdownSimulationResponse(BaseModel):
    battery_summary: Dict[str, Any]
    timeline: List[ShutdownTimelinePoint]
    device_statuses: List[ShutdownDeviceStatus]


class ShutdownSimulationRequest(BaseModel):
    rack_id: Optional[int] = None
    battery_type: str = "vrla"
    series_blocks: int = Field(4, gt=0)
    parallel_strings: int = Field(1, gt=0)
    block_voltage_v: Decimal = Field(Decimal("12"), gt=0)
    block_capacity_ah: Decimal = Field(Decimal("100"), gt=0)
    age_years: Decimal = Field(Decimal("0"), ge=0)
    temperature_c: Decimal = Field(Decimal("20"), ge=-273.15)
    inverter_efficiency: Decimal = Field(Decimal("0.90"), gt=0, le=1)


@router.post("/simulate-shutdown", response_model=ShutdownSimulationResponse)
async def simulate_shutdown(
    req: ShutdownSimulationRequest, db: AsyncSession = Depends(get_db)
):
    if req.rack_id is not None:
        result = await db.execute(
            select(DeviceModel).where(DeviceModel.rack_id == req.rack_id)
        )
    else:
        result = await db.execute(
            select(DeviceModel)
        )
    devices = result.scalars().all()

    if not devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keine Geräte gefunden" if req.rack_id is None else f"Keine Geräte im Rack {req.rack_id} gefunden",
        )

    device_dicts = [
        {
            "id": d.id,
            "hostname": d.hostname,
            "typ": d.typ,
            "tdp_watt": float(d.tdp_watt) if d.tdp_watt else 0,
            "shutdown_delay_seconds": d.shutdown_delay_seconds or 0,
            "shutdown_priority": d.shutdown_priority or 2,
        }
        for d in devices
    ]

    # Sort by shutdown_priority (1=critical last), then by delay
    device_dicts.sort(
        key=lambda x: (x["shutdown_priority"], x["shutdown_delay_seconds"])
    )

    sim_result = ShutdownSimulationEngine.simulate_shutdown(
        battery_type=req.battery_type,
        series_blocks=req.series_blocks,
        parallel_strings=req.parallel_strings,
        block_voltage_v=req.block_voltage_v,
        block_capacity_ah=req.block_capacity_ah,
        age_years=req.age_years,
        temperature_c=req.temperature_c,
        inverter_efficiency=req.inverter_efficiency,
        devices=device_dicts,
    )

    return sim_result
