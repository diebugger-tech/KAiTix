import asyncio
from app.core.database import AsyncSessionLocal
from app.models import Rack, Device

async def main():
    async with AsyncSessionLocal() as db:
        racks = [
            Rack(name="RACK-HOT-01", standort="Serverraum 1", rackreihe="Reihe A", hoehe_u=42, cooling_capacity_w=5000),
            Rack(name="RACK-COOL-01", standort="Serverraum 1", rackreihe="Reihe B", hoehe_u=42, cooling_capacity_w=15000),
        ]
        db.add_all(racks)
        await db.flush()

        rack_hot, rack_cool = racks

        devices = [
            # HOT RACK (Cooling 5000W, Total TDP 6500W -> RED OVERHEAT!)
            Device(hostname="srv-ai-node-1", typ="server", rack_id=rack_hot.id, u_position=10, u_hoehe=4, tdp_watt=2000, hersteller="NVIDIA", modell="DGX A100"),
            Device(hostname="srv-ai-node-2", typ="server", rack_id=rack_hot.id, u_position=15, u_hoehe=4, tdp_watt=2000, hersteller="NVIDIA", modell="DGX A100"),
            Device(hostname="srv-ai-node-3", typ="server", rack_id=rack_hot.id, u_position=20, u_hoehe=4, tdp_watt=2000, hersteller="NVIDIA", modell="DGX A100"),
            Device(hostname="sw-core-hot", typ="switch", rack_id=rack_hot.id, u_position=40, u_hoehe=1, tdp_watt=500, hersteller="Cisco", modell="Nexus 9k"),
            Device(hostname="pp-core-hot", typ="patchpanel", rack_id=rack_hot.id, u_position=42, u_hoehe=1, tdp_watt=0, hersteller="Corning", modell="Edge 48"),

            # COOL RACK (Cooling 15000W, Total TDP 3000W -> GREEN/ORANGE OK!)
            Device(hostname="srv-web-01", typ="server", rack_id=rack_cool.id, u_position=1, u_hoehe=2, tdp_watt=500, hersteller="Dell", modell="R750"),
            Device(hostname="srv-web-02", typ="server", rack_id=rack_cool.id, u_position=4, u_hoehe=2, tdp_watt=500, hersteller="Dell", modell="R750"),
            Device(hostname="srv-web-03", typ="server", rack_id=rack_cool.id, u_position=7, u_hoehe=2, tdp_watt=500, hersteller="Dell", modell="R750"),
            Device(hostname="san-storage-1", typ="storage", rack_id=rack_cool.id, u_position=15, u_hoehe=4, tdp_watt=1500, hersteller="NetApp", modell="AFF A400"),
            Device(hostname="pp-core-cool", typ="patchpanel", rack_id=rack_cool.id, u_position=41, u_hoehe=2, tdp_watt=0, hersteller="CommScope", modell="SYSTIMAX"),
        ]
        db.add_all(devices)
        await db.commit()
        print(f"Demo UX Seed erfolgreich: {len(racks)} Racks, {len(devices)} Devices erzeugt.")

if __name__ == "__main__":
    asyncio.run(main())
