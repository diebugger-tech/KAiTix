import asyncio
from app.core.database import AsyncSessionLocal
from app.domains.hardware.models import Device
from sqlalchemy import select


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Device).where(Device.typ == "pdu"))
        pdus = result.scalars().all()
        for p in pdus:
            print(f"{p.hostname} - Rack ID: {p.rack_id} - Side: {p.side}")


asyncio.run(main())
