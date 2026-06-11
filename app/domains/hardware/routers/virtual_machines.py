from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.domains.hardware.models import VirtualMachine as VirtualMachineModel
from app.domains.hardware.schemas import (
    VirtualMachine,
    VirtualMachineCreate,
    VirtualMachineUpdate,
    VirtualMachineReorder,
)
from app.domains.network.services.ipam_service import (
    validate_and_check_ip,
    validate_and_check_ipv6,
)

router = APIRouter()


async def check_circular_dependency(
    db: AsyncSession, vm_id: int, depends_on_vm_id: int | None
):
    if not depends_on_vm_id:
        return
    if vm_id == depends_on_vm_id:
        raise HTTPException(
            status_code=400,
            detail="Zirkuläre Abhängigkeit erkannt: VM kann nicht von sich selbst abhängen.",
        )

    result = await db.execute(
        select(VirtualMachineModel.id, VirtualMachineModel.depends_on_vm_id)
    )
    vms = result.all()
    dep_map = {row.id: row.depends_on_vm_id for row in vms}

    dep_map[vm_id] = depends_on_vm_id
    current_dep = depends_on_vm_id
    visited = set()

    while current_dep:
        if current_dep == vm_id:
            raise HTTPException(
                status_code=400,
                detail="Zirkuläre Abhängigkeit erkannt: Diese Zuweisung führt zu einer Endlosschleife.",
            )
        if current_dep in visited:
            break
        visited.add(current_dep)
        current_dep = dep_map.get(current_dep)


@router.get("/", response_model=List[VirtualMachine])
async def list_virtual_machines(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VirtualMachineModel))
    return result.scalars().all()


@router.post("/", response_model=VirtualMachine, status_code=status.HTTP_201_CREATED)
async def create_virtual_machine(
    vm_in: VirtualMachineCreate, db: AsyncSession = Depends(get_db)
):
    db_vm = VirtualMachineModel(**vm_in.model_dump())
    if db_vm.host_device_id is None:
        raise HTTPException(status_code=422, detail="host_device_id is required")

    # IP Validation
    if db_vm.ip_adresse:
        db_vm.ip_adresse = await validate_and_check_ip(db, db_vm.ip_adresse)
    if db_vm.ipv6_adresse:
        db_vm.ipv6_adresse = await validate_and_check_ipv6(db, db_vm.ipv6_adresse)

    # Note: For creation, vm_id doesn't exist yet, but we can assign a dummy id like -1 to check cycle
    await check_circular_dependency(db, -1, db_vm.depends_on_vm_id)

    db.add(db_vm)
    await db.commit()
    await db.refresh(db_vm)
    return db_vm


@router.get("/{vm_id}", response_model=VirtualMachine)
async def get_virtual_machine(vm_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VirtualMachineModel).where(VirtualMachineModel.id == vm_id)
    )
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(status_code=404, detail="Virtual machine not found")
    return vm


@router.put("/{vm_id}", response_model=VirtualMachine)
async def update_virtual_machine(
    vm_id: int, vm_in: VirtualMachineUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(VirtualMachineModel).where(VirtualMachineModel.id == vm_id)
    )
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(status_code=404, detail="Virtual machine not found")

    update_data = vm_in.model_dump(exclude_unset=True)
    if "host_device_id" in update_data and update_data["host_device_id"] is None:
        raise HTTPException(status_code=422, detail="host_device_id is required")

    for field, value in update_data.items():
        setattr(vm, field, value)

    # IP Validation
    if vm.ip_adresse:
        vm.ip_adresse = await validate_and_check_ip(
            db, vm.ip_adresse, exclude_vm_id=vm.id
        )
    if vm.ipv6_adresse:
        vm.ipv6_adresse = await validate_and_check_ipv6(
            db, vm.ipv6_adresse, exclude_vm_id=vm.id
        )

    await check_circular_dependency(db, vm.id, vm.depends_on_vm_id)

    await db.commit()
    await db.refresh(vm)
    return vm


@router.put("/reorder", response_model=List[VirtualMachine])
async def reorder_virtual_machines(
    reorders: List[VirtualMachineReorder], db: AsyncSession = Depends(get_db)
):
    vm_ids = [r.id for r in reorders]
    if not vm_ids:
        return []

    result = await db.execute(
        select(VirtualMachineModel).where(VirtualMachineModel.id.in_(vm_ids))
    )
    vms = {vm.id: vm for vm in result.scalars().all()}

    for r in reorders:
        if r.id in vms:
            vms[r.id].shutdown_priority = r.shutdown_priority

    await db.commit()
    return list(vms.values())


@router.delete("/{vm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_virtual_machine(vm_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VirtualMachineModel).where(VirtualMachineModel.id == vm_id)
    )
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(status_code=404, detail="Virtual machine not found")

    await db.delete(vm)
    await db.commit()
