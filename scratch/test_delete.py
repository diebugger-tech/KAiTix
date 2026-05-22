import asyncio
from app.core.database import AsyncSessionLocal
from app.models import Rack
from sqlalchemy import select


async def main():
    async with AsyncSessionLocal() as session:
        # Get RACK-01
        result = await session.execute(select(Rack).where(Rack.name == "RACK-01"))
        rack = result.scalar_one_or_none()
        if not rack:
            print("RACK-01 not found!")
            return

        print(f"Found rack: {rack.name} (ID: {rack.id})")
        try:
            await session.delete(rack)
            await session.commit()
            print("Successfully deleted!")
        except Exception:
            print("ERROR occurred during delete:")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
