import ipaddress
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domains.hardware.models import Device, VirtualMachine

async def validate_and_check_ip(
    db: AsyncSession,
    ip_str: Optional[str],
    exclude_device_id: Optional[int] = None,
    exclude_vm_id: Optional[int] = None
) -> Optional[str]:
    if not ip_str:
        return None
    
    # 1. Normalize
    try:
        normalized_ip = str(ipaddress.ip_address(ip_str.strip()))
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungültige IP-Adresse")

    # 2. Global Collision Check
    # Check Devices
    stmt_device = select(Device).where(Device.ip_adresse == normalized_ip)
    if exclude_device_id:
        stmt_device = stmt_device.where(Device.id != exclude_device_id)
    
    res_dev = await db.execute(stmt_device)
    if res_dev.scalars().first():
        raise HTTPException(status_code=400, detail="IP-Adresse wird bereits von einem Gerät verwendet")

    # Check VMs
    stmt_vm = select(VirtualMachine).where(VirtualMachine.ip_adresse == normalized_ip)
    if exclude_vm_id:
        stmt_vm = stmt_vm.where(VirtualMachine.id != exclude_vm_id)
        
    res_vm = await db.execute(stmt_vm)
    if res_vm.scalars().first():
        raise HTTPException(status_code=400, detail="IP-Adresse wird bereits von einer VM verwendet")

    return normalized_ip
