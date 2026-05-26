"""Seed-Script: Erzeugt realistische Testdaten für die Topologie-Ansicht.

Aufruf: python scripts/seed_testdaten.py
"""

import asyncio
from app.core.database import AsyncSessionLocal
from app.models import Rack, Device, Cable, PduOutlet


async def main():
    async with AsyncSessionLocal() as db:
        racks = [
            Rack(name="Rack-A", standort="DC1", rackreihe="Reihe 1", hoehe_u=42),
            Rack(name="Rack-B", standort="DC1", rackreihe="Reihe 2", hoehe_u=42),
        ]
        db.add_all(racks)
        await db.flush()

        rack_a, rack_b = racks

        devices = [
            Device(
                hostname="srv-web-01",
                typ="server",
                rack_id=rack_a.id,
                u_position=30,
                u_hoehe=2,
                tdp_watt=450,
                hersteller="Dell",
                modell="PowerEdge R750",
            ),
            Device(
                hostname="srv-db-01",
                typ="server",
                rack_id=rack_a.id,
                u_position=26,
                u_hoehe=2,
                tdp_watt=800,
                hersteller="HPE",
                modell="ProLiant DL380",
            ),
            Device(
                hostname="srv-app-01",
                typ="server",
                rack_id=rack_b.id,
                u_position=30,
                u_hoehe=2,
                tdp_watt=550,
                hersteller="Dell",
                modell="PowerEdge R650",
            ),
            Device(
                hostname="sw-core-01",
                typ="switch",
                rack_id=rack_a.id,
                u_position=40,
                u_hoehe=1,
                tdp_watt=120,
                hersteller="Cisco",
                modell="Catalyst 9500",
            ),
            Device(
                hostname="pdu-a-01",
                typ="pdu",
                rack_id=rack_a.id,
                u_position=None,
                u_hoehe=0,
                side="left",
            ),
            Device(
                hostname="pdu-b-01",
                typ="pdu",
                rack_id=rack_b.id,
                u_position=None,
                u_hoehe=0,
                side="left",
            ),
        ]
        db.add_all(devices)
        await db.flush()

        srv_web, srv_db, srv_app, switch, pdu_a, pdu_b = devices

        cables = [
            Cable(
                kabel_nr="KAB-0001",
                typ="Cat6",
                laenge_m=3,
                farbe="Blau",
                von_device_id=srv_web.id,
                von_port="eth0",
                nach_device_id=switch.id,
                nach_port="Gi1/0/1",
            ),
            Cable(
                kabel_nr="KAB-0002",
                typ="Cat6",
                laenge_m=3,
                farbe="Blau",
                von_device_id=srv_db.id,
                von_port="eth0",
                nach_device_id=switch.id,
                nach_port="Gi1/0/2",
            ),
            Cable(
                kabel_nr="KAB-0003",
                typ="Cat6",
                laenge_m=5,
                farbe="Blau",
                von_device_id=srv_app.id,
                von_port="eth0",
                nach_device_id=switch.id,
                nach_port="Gi1/0/3",
            ),
            Cable(
                kabel_nr="KAB-0004",
                typ="Strom-C13",
                laenge_m=2,
                farbe="Rot",
                von_device_id=pdu_a.id,
                von_port="Out1",
                nach_device_id=srv_web.id,
                nach_port="PSU1",
            ),
            Cable(
                kabel_nr="KAB-0005",
                typ="Strom-C13",
                laenge_m=2,
                farbe="Rot",
                von_device_id=pdu_a.id,
                von_port="Out2",
                nach_device_id=srv_db.id,
                nach_port="PSU1",
            ),
            Cable(
                kabel_nr="KAB-0006",
                typ="Strom-C13",
                laenge_m=2,
                farbe="Rot",
                von_device_id=pdu_b.id,
                von_port="Out1",
                nach_device_id=srv_app.id,
                nach_port="PSU1",
            ),
            Cable(
                kabel_nr="KAB-0007",
                typ="Strom-C19",
                laenge_m=2,
                farbe="Rot",
                von_device_id=pdu_a.id,
                von_port="Out3",
                nach_device_id=switch.id,
                nach_port="PSU1",
            ),
        ]
        db.add_all(cables)
        await db.flush()

        outlets = [
            PduOutlet(
                pdu_id=pdu_a.id,
                outlet_name="Out1",
                phase="L1",
                steckdosentyp="C13",
                max_watt=2500,
                schaltbar=True,
                connected_device_id=srv_web.id,
                connected_port="PSU1",
            ),
            PduOutlet(
                pdu_id=pdu_a.id,
                outlet_name="Out2",
                phase="L2",
                steckdosentyp="C13",
                max_watt=2500,
                schaltbar=True,
                connected_device_id=srv_db.id,
                connected_port="PSU1",
            ),
            PduOutlet(
                pdu_id=pdu_a.id,
                outlet_name="Out3",
                phase="L3",
                steckdosentyp="C19",
                max_watt=4000,
                schaltbar=True,
                connected_device_id=switch.id,
                connected_port="PSU1",
            ),
            PduOutlet(
                pdu_id=pdu_b.id,
                outlet_name="Out1",
                phase="L1",
                steckdosentyp="C13",
                max_watt=2500,
                schaltbar=True,
                connected_device_id=srv_app.id,
                connected_port="PSU1",
            ),
        ]
        db.add_all(outlets)
        await db.flush()

        await db.commit()
        print(
            f"Seed erfolgreich: 2 Racks, {len(devices)} Devices, {len(cables)} Cables, {len(outlets)} PDU Outlets"
        )


if __name__ == "__main__":
    asyncio.run(main())
