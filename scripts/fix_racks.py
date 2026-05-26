import asyncio
from sqlalchemy import text
import os
import sys

# Ensure project root is in sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal

async def migrate_racks():
    async with AsyncSessionLocal() as session:
        # Fetch all racks
        result = await session.execute(text("SELECT id, name, standort, rackreihe FROM racks"))
        racks = result.fetchall()
        
        for rack in racks:
            rack_id, name, standort, rackreihe = rack
            # If the standort is something like "RZ1-ReiheA", split it
            if standort and "RZ1-Reihe" in standort:
                reihe = standort.split("-")[1]
                reihe_formatted = reihe.replace("Reihe", "Reihe ")
                new_standort = "Rechenzentrum 1"
                
                print(f"Updating Rack {name}: standort='{new_standort}', rackreihe='{reihe_formatted}'")
                await session.execute(
                    text("UPDATE racks SET standort = :standort, rackreihe = :rackreihe WHERE id = :id"),
                    {"standort": new_standort, "rackreihe": reihe_formatted, "id": rack_id}
                )
            # Also handle other similar formats if any
            elif standort and "RZ1-ReiheB" in standort:
                new_standort = "Rechenzentrum 1"
                reihe_formatted = "Reihe B"
                print(f"Updating Rack {name}: standort='{new_standort}', rackreihe='{reihe_formatted}'")
                await session.execute(
                    text("UPDATE racks SET standort = :standort, rackreihe = :rackreihe WHERE id = :id"),
                    {"standort": new_standort, "rackreihe": reihe_formatted, "id": rack_id}
                )
        
        await session.commit()
    print("Database update complete.")

if __name__ == "__main__":
    asyncio.run(migrate_racks())
