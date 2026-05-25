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
)
from app.domains.network.services.ipam_service import validate_and_check_ip

router = APIRouter()

@router.get("/", response_model=List[VirtualMachine])
async def list_virtual_machines(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VirtualMachineModel)
    )
    return result.scalars().all()

@router.post("/", response_model=VirtualMachine, status_code=status.HTTP_201_CREATED)
async def create_virtual_machine(vm_in: VirtualMachineCreate, db: AsyncSession = Depends(get_db)):
    db_vm = VirtualMachineModel(**vm_in.model_dump())
    if db_vm.host_device_id is None:
        raise HTTPException(status_code=422, detail="host_device_id is required")
        
    # IP Validation
    if db_vm.ip_adresse:
        db_vm.ip_adresse = await validate_and_check_ip(db, db_vm.ip_adresse)

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
        vm.ip_adresse = await validate_and_check_ip(db, vm.ip_adresse, exclude_vm_id=vm.id)

    # Simple circular dependency check
    if vm.depends_on_vm_id == vm.id:
        raise HTTPException(status_code=400, detail="Circular dependency: VM cannot depend on itself")

    await db.commit()
    await db.refresh(vm)
    return vm

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
