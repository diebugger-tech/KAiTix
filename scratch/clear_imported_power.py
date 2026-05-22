import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Rack, Device, Cable


async def main():
    async with AsyncSessionLocal() as session:
        # Delete cables starting with W-
        cables_to_del = (
            (await session.execute(select(Cable).where(Cable.kabel_nr.like("W-%"))))
            .scalars()
            .all()
        )
        for c in cables_to_del:
            print(f"Deleting cable: {c.kabel_nr}")
            await session.delete(c)

        # Delete devices
        hostnames = [
            "HV-RZ-01",
            "UV-RZ-01",
            "USV-Schrank-40kW",
            "MBS-Bypass",
            "UV-USV-01",
            "SmartPDU-A-0UL",
            "SmartPDU-A-0UR",
            "SmartPDU-B-0UL",
        ]
        for h in hostnames:
            dev = (
                await session.execute(select(Device).where(Device.hostname == h))
            ).scalar_one_or_none()
            if dev:
                print(f"Deleting device: {dev.hostname}")
                await session.delete(dev)

        # Delete rack "Verteilerraum"
        rack = (
            await session.execute(select(Rack).where(Rack.name == "Verteilerraum"))
        ).scalar_one_or_none()
        if rack:
            print(f"Deleting rack: {rack.name}")
            await session.delete(rack)

        await session.commit()
        print("Cleaned up database for power import.")


if __name__ == "__main__":
    asyncio.run(main())
