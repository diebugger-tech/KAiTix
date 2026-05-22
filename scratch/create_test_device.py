import asyncio
from app.core.database import async_session_maker
from app.models import Device


async def main():
    async with async_session_maker() as db:
        try:
            device = Device(
                hostname="7",
                typ="server",
                rack_id=30,
                u_position=16,
                u_hoehe=1,
                phase="L1",
                anschlussleistung_watt=250,
            )
            db.add(device)
            await db.commit()
            print("Success")
        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
