from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response, Header
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from app.core.database import get_db

from app.domains.runbooks.models import (
    Runbook as RunbookModel,
    RunbookLayer as RunbookLayerModel,
    RunbookDevice as RunbookDeviceModel,
    RunbookExecution as RunbookExecutionModel,
    RunbookExecutionStep as RunbookExecutionStepModel,
)
from app.domains.hardware.models import Device, VirtualMachine

from app.domains.runbooks.schemas import (
    Runbook, RunbookCreate, RunbookUpdate,
    RunbookLayer, RunbookLayerCreate, RunbookLayerUpdate, RunbookLayerReorderRequest,
    RunbookDevice, RunbookDeviceCreate, RunbookDeviceUpdate, RunbookDeviceReorderRequest,
    RunbookExecution, RunbookExecutionCreate, RunbookExecutionStatusUpdate,
    RunbookExecutionStep, RunbookExecutionStepCheckRequest
)

router = APIRouter()
executions_router = APIRouter()

# === RUNBOOKS ===

@router.get("/", response_model=List[Runbook])
async def list_runbooks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RunbookModel)
        .options(
            selectinload(RunbookModel.layers).selectinload(RunbookLayerModel.devices).selectinload(RunbookDeviceModel.device),
            selectinload(RunbookModel.layers).selectinload(RunbookLayerModel.devices).selectinload(RunbookDeviceModel.vm),
        )
    )
    return result.scalars().unique().all()

@router.post("/", response_model=Runbook, status_code=status.HTTP_201_CREATED)
async def create_runbook(
    runbook_in: RunbookCreate,
    db: AsyncSession = Depends(get_db),
    x_username: Optional[str] = Header(None, alias="X-Username")
):
    db_runbook = RunbookModel(**runbook_in.model_dump(), erstellt_von=x_username)
    db.add(db_runbook)
    await db.commit()
    await db.refresh(db_runbook)
    return db_runbook

@router.get("/{id}", response_model=Runbook)
async def get_runbook(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RunbookModel)
        .where(RunbookModel.id == id)
        .options(
            selectinload(RunbookModel.layers).selectinload(RunbookLayerModel.devices).selectinload(RunbookDeviceModel.device),
            selectinload(RunbookModel.layers).selectinload(RunbookLayerModel.devices).selectinload(RunbookDeviceModel.vm),
        )
    )
    runbook = result.scalar_one_or_none()
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return runbook

@router.put("/{id}", response_model=Runbook)
async def update_runbook(id: int, runbook_in: RunbookUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RunbookModel).where(RunbookModel.id == id))
    runbook = result.scalar_one_or_none()
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")
    
    update_data = runbook_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(runbook, field, value)
        
    await db.commit()
    await db.refresh(runbook)
    return runbook

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_runbook(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RunbookModel).where(RunbookModel.id == id))
    runbook = result.scalar_one_or_none()
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")
    await db.delete(runbook)
    await db.commit()

# === LAYERS ===

@router.get("/{id}/layers", response_model=List[RunbookLayer])
async def list_layers(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RunbookLayerModel).where(RunbookLayerModel.runbook_id == id).order_by(RunbookLayerModel.position)
    )
    return result.scalars().all()

@router.post("/{id}/layers", response_model=RunbookLayer, status_code=status.HTTP_201_CREATED)
async def create_layer(id: int, layer_in: RunbookLayerCreate, db: AsyncSession = Depends(get_db)):
    db_layer = RunbookLayerModel(**layer_in.model_dump(), runbook_id=id)
    db.add(db_layer)
    await db.commit()
    await db.refresh(db_layer)
    return db_layer

@router.put("/{id}/layers/reorder", status_code=status.HTTP_200_OK)
async def reorder_layers(id: int, req: RunbookLayerReorderRequest, db: AsyncSession = Depends(get_db)):
    for idx, layer_id in enumerate(req.layer_ids):
        await db.execute(
            update(RunbookLayerModel)
            .where(RunbookLayerModel.id == layer_id, RunbookLayerModel.runbook_id == id)
            .values(position=idx + 1)
        )
    await db.commit()
    return {"status": "ok"}

@router.put("/{id}/layers/{lid}", response_model=RunbookLayer)
async def update_layer(id: int, lid: int, layer_in: RunbookLayerUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RunbookLayerModel).where(RunbookLayerModel.id == lid, RunbookLayerModel.runbook_id == id))
    layer = result.scalar_one_or_none()
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
        
    update_data = layer_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(layer, field, value)
        
    await db.commit()
    await db.refresh(layer)
    return layer

@router.delete("/{id}/layers/{lid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_layer(id: int, lid: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RunbookLayerModel).where(RunbookLayerModel.id == lid, RunbookLayerModel.runbook_id == id))
    layer = result.scalar_one_or_none()
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
    await db.delete(layer)
    await db.commit()

# === DEVICES ===

@router.post("/{id}/devices", response_model=RunbookDevice, status_code=status.HTTP_201_CREATED)
async def create_runbook_device(id: int, device_in: RunbookDeviceCreate, db: AsyncSession = Depends(get_db)):
    db_device = RunbookDeviceModel(**device_in.model_dump(), runbook_id=id)
    db.add(db_device)
    await db.commit()
    await db.refresh(db_device)
    return db_device

@router.put("/{id}/devices/reorder", status_code=status.HTTP_200_OK)
async def reorder_devices(id: int, req: RunbookDeviceReorderRequest, db: AsyncSession = Depends(get_db)):
    for idx, dev_id in enumerate(req.device_ids):
        await db.execute(
            update(RunbookDeviceModel)
            .where(RunbookDeviceModel.id == dev_id, RunbookDeviceModel.runbook_id == id)
            .values(position=idx + 1)
        )
    await db.commit()
    return {"status": "ok"}

@router.put("/{id}/devices/{did}", response_model=RunbookDevice)
async def update_runbook_device(id: int, did: int, device_in: RunbookDeviceUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RunbookDeviceModel).where(RunbookDeviceModel.id == did, RunbookDeviceModel.runbook_id == id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    update_data = device_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)
        
    await db.commit()
    await db.refresh(device)
    return device

@router.delete("/{id}/devices/{did}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_runbook_device(id: int, did: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RunbookDeviceModel).where(RunbookDeviceModel.id == did, RunbookDeviceModel.runbook_id == id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    await db.delete(device)
    await db.commit()

# === EXECUTIONS ===

@router.post("/{id}/execute", response_model=RunbookExecution, status_code=status.HTTP_201_CREATED)
async def execute_runbook(
    id: int,
    exec_in: RunbookExecutionCreate,
    db: AsyncSession = Depends(get_db),
    x_username: Optional[str] = Header(None, alias="X-Username")
):
    if exec_in.runbook_id != id:
        raise HTTPException(status_code=400, detail="Runbook ID mismatch")
        
    db_exec = RunbookExecutionModel(**exec_in.model_dump(), gestartet_von=x_username)
    db.add(db_exec)
    await db.commit()
    await db.refresh(db_exec)
    return db_exec

@executions_router.get("/{eid}", response_model=RunbookExecution)
async def get_execution(eid: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RunbookExecutionModel)
        .where(RunbookExecutionModel.id == eid)
        .options(selectinload(RunbookExecutionModel.steps))
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution

@executions_router.post("/{eid}/steps/{sid}/check", response_model=RunbookExecutionStep)
async def check_execution_step(
    eid: int,
    sid: int,
    req: RunbookExecutionStepCheckRequest,
    db: AsyncSession = Depends(get_db),
    x_username: Optional[str] = Header(None, alias="X-Username")
):
    result = await db.execute(
        select(RunbookExecutionStepModel)
        .where(
            RunbookExecutionStepModel.runbook_device_id == sid,
            RunbookExecutionStepModel.execution_id == eid
        )
    )
    step = result.scalar_one_or_none()
    if not step:
        step = RunbookExecutionStepModel(
            execution_id=eid,
            runbook_device_id=sid,
            abgehakt_am=datetime.utcnow(),
            abgehakt_von=x_username,
            note=req.note
        )
        db.add(step)
    else:
        step.abgehakt_am = datetime.utcnow()
        step.abgehakt_von = x_username
        if req.note is not None:
            step.note = req.note

    await db.commit()
    await db.refresh(step)
    return step

@executions_router.delete("/{eid}/steps/{sid}/uncheck", status_code=status.HTTP_204_NO_CONTENT)
async def uncheck_execution_step(
    eid: int,
    sid: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(RunbookExecutionStepModel)
        .where(
            RunbookExecutionStepModel.runbook_device_id == sid,
            RunbookExecutionStepModel.execution_id == eid
        )
    )
    step = result.scalar_one_or_none()
    if step:
        await db.delete(step)
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@executions_router.put("/{eid}/status", response_model=RunbookExecution)
async def update_execution_status(eid: int, req: RunbookExecutionStatusUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RunbookExecutionModel).where(RunbookExecutionModel.id == eid))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    execution.status = req.status
    await db.commit()
    await db.refresh(execution)
    return execution

# === STARTUP GENERATION ===

@router.post("/{id}/generate-startup", response_model=Runbook)
async def generate_startup(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RunbookModel)
        .where(RunbookModel.id == id)
        .options(selectinload(RunbookModel.layers).selectinload(RunbookLayerModel.devices))
    )
    shutdown_runbook = result.scalar_one_or_none()
    if not shutdown_runbook or shutdown_runbook.typ != "shutdown":
        raise HTTPException(status_code=400, detail="Must generate from a 'shutdown' runbook")

    startup_runbook = RunbookModel(
        name=f"{shutdown_runbook.name} — Startup",
        typ="startup",
        beschreibung=shutdown_runbook.beschreibung,
        generated_from_id=id
    )
    db.add(startup_runbook)
    await db.flush() # get id

    # reverse layers
    sorted_layers = sorted(shutdown_runbook.layers, key=lambda x: x.position, reverse=True)
    
    for layer_idx, old_layer in enumerate(sorted_layers):
        new_layer = RunbookLayerModel(
            runbook_id=startup_runbook.id,
            position=layer_idx + 1,
            name=old_layer.name,
            # DO NOT COPY markdown_note
            markdown_note=None 
        )
        db.add(new_layer)
        await db.flush()

        # copy devices (keep their relative order within the layer, or reverse it? Prompt says:
        # "Alle Geräte/VMs mit delay_seconds, responsible, position kopieren")
        # Let's keep position.
        for old_dev in old_layer.devices:
            new_dev = RunbookDeviceModel(
                runbook_id=startup_runbook.id,
                layer_id=new_layer.id,
                device_id=old_dev.device_id,
                vm_id=old_dev.vm_id,
                freitext=old_dev.freitext,
                delay_seconds=old_dev.delay_seconds,
                responsible=old_dev.responsible,
                position=old_dev.position,
                # DO NOT COPY note
                note=None
            )
            db.add(new_dev)

    await db.commit()
    await db.refresh(startup_runbook)
    return startup_runbook

# === EXPORT ===

@router.get("/{id}/export/markdown")
async def export_markdown(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RunbookModel)
        .where(RunbookModel.id == id)
        .options(
            selectinload(RunbookModel.layers).selectinload(RunbookLayerModel.devices).selectinload(RunbookDeviceModel.device),
            selectinload(RunbookModel.layers).selectinload(RunbookLayerModel.devices).selectinload(RunbookDeviceModel.vm),
        )
    )
    runbook = result.scalar_one_or_none()
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")

    lines = []
    lines.append(f"# Runbook: {runbook.name}")
    lines.append(f"**Typ:** {runbook.typ} | **Erstellt:** {runbook.erstellt_am.strftime('%Y-%m-%d %H:%M')} | **Von:** {runbook.erstellt_von or 'System'}")
    if runbook.beschreibung:
        lines.append(runbook.beschreibung)
    
    lines.append("\n---\n")
    lines.append("## " + ("SHUTDOWN-SEQUENZ" if runbook.typ == "shutdown" else "STARTUP-SEQUENZ (umgekehrt)" if runbook.typ == "startup" else f"{runbook.typ.upper()}-SEQUENZ"))
    
    sorted_layers = sorted(runbook.layers, key=lambda x: x.position)
    
    for layer in sorted_layers:
        lines.append(f"\n### Ebene {layer.position}: {layer.name}")
        if layer.markdown_note:
            lines.append(f"> {layer.markdown_note}")
        lines.append("")
        
        sorted_devices = sorted(layer.devices, key=lambda x: x.position)
        for dev in sorted_devices:
            ident = dev.freitext or (dev.vm.name if dev.vm else (dev.device.hostname if dev.device else "Unknown"))
            resp = f" — {dev.responsible}" if dev.responsible else ""
            lines.append(f"- [ ] {ident} ({dev.delay_seconds}s){resp}")
            if dev.note:
                lines.append(f"      _Notiz: {dev.note}_")

    return PlainTextResponse("\n".join(lines), media_type="text/markdown")

@router.get("/{id}/export/pdf")
async def export_pdf(id: int):
    # Dummy endpoint for PDF
    return {"message": "PDF export not implemented in python backend yet, normally done via frontend print"}

@router.get("/{id}/executions", response_model=List[RunbookExecution])
async def get_runbook_executions(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RunbookExecutionModel)
        .where(RunbookExecutionModel.runbook_id == id)
        .options(selectinload(RunbookExecutionModel.steps))
        .order_by(RunbookExecutionModel.gestartet_am.desc())
    )
    return result.scalars().all()
