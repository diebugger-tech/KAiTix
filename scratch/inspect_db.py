import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Rack, Device, Cable


async def main():
    async with AsyncSessionLocal() as session:
        racks = (await session.execute(select(Rack))).scalars().all()
        print(f"=== RACKS ({len(racks)}) ===")
        for r in racks:
            print(f"ID: {r.id}, Name: {r.name}, Standort: {r.standort}")

        devices = (await session.execute(select(Device))).scalars().all()
        print(f"\n=== DEVICES ({len(devices)}) ===")
        for d in devices:
            print(
                f"ID: {d.id}, Hostname: {d.hostname}, Typ: {d.typ}, Rack ID: {d.rack_id}"
            )

        cables = (await session.execute(select(Cable))).scalars().all()
        print(f"\n=== CABLES ({len(cables)}) ===")
        for c in cables:
            print(
                f"ID: {c.id}, Kabel Nr: {c.kabel_nr}, Typ: {c.typ}, Von: {c.von_device_id}:{c.von_port} -> Nach: {c.nach_device_id}:{c.nach_port}"
            )


if __name__ == "__main__":
    asyncio.run(main())
