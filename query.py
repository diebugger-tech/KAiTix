import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        # Update
        await session.execute(text("UPDATE usv_units SET battery_strings = 2 WHERE id = 1;"))
        await session.commit()
        
        # Select
        result = await session.execute(text("SELECT id, bezeichnung, battery_strings FROM usv_units;"))
        rows = result.fetchall()
        print(f"| {'id':<4} | {'bezeichnung':<30} | {'battery_strings':<15} |")
        print("-" * 57)
        for row in rows:
            print(f"| {row[0]:<4} | {row[1]:<30} | {row[2]:<15} |")

asyncio.run(main())
