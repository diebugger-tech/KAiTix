import asyncio
from sqlalchemy import delete
from app.core.database import AsyncSessionLocal
from app.models import Rack, Device, Cable, PduOutlet


async def main():
    async with AsyncSessionLocal() as db:
        # 1. Orphaned cables löschen (referenzieren nicht-existente Devices)
        result = await db.execute(
            delete(Cable).where(
                Cable.von_device_id.is_(None) | Cable.nach_device_id.is_(None)
            )
        )
        print(f"Orphaned cables deleted: {result.rowcount}")

        # 2. Racks anlegen
        rack_a = Rack(
            name="Rack-A", standort="DC1 Reihe 1", hoehe_u=42, bemerkung="Demo Rack A"
        )
        rack_b = Rack(
            name="Rack-B", standort="DC1 Reihe 2", hoehe_u=42, bemerkung="Demo Rack B"
        )
        db.add_all([rack_a, rack_b])
        await db.flush()

        # 3. Devices anlegen
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
                tdp_watt=350,
                hersteller="HPE",
                modell="ProLiant DL380",
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
                hostname="fw-edge-01",
                typ="firewall",
                rack_id=rack_b.id,
                u_position=36,
                u_hoehe=1,
                tdp_watt=200,
                hersteller="Fortinet",
                modell="FortiGate 600F",
            ),
            Device(
                hostname="st-nas-01",
                typ="storage",
                rack_id=rack_b.id,
                u_position=26,
                u_hoehe=4,
                tdp_watt=600,
                hersteller="NetApp",
                modell="AFF A250",
            ),
            Device(
                hostname="pdu-a-01",
                typ="pdu",
                rack_id=rack_a.id,
                u_position=0,
                u_hoehe=0,
                tdp_watt=0,
                hersteller="Kentix",
                modell="SmartPDU 40HE",
            ),
            Device(
                hostname="pdu-b-01",
                typ="pdu",
                rack_id=rack_b.id,
                u_position=0,
                u_hoehe=0,
                tdp_watt=0,
                hersteller="Kentix",
                modell="SmartPDU 40HE",
            ),
        ]
        db.add_all(devices)
        await db.flush()

        srv1, srv2, switch, fw, storage, pdu_a, pdu_b = devices

        # 4. Cables anlegen (intra-rack + cross-rack)
        cables = [
            Cable(
                kabel_nr="KAB-0001",
                typ="Cat6A",
                laenge_m=3,
                farbe="blau",
                von_device_id=srv1.id,
                von_port="eth0",
                nach_device_id=switch.id,
                nach_port="Gi1/0/1",
            ),
            Cable(
                kabel_nr="KAB-0002",
                typ="Cat6A",
                laenge_m=3,
                farbe="blau",
                von_device_id=srv2.id,
                von_port="eth0",
                nach_device_id=switch.id,
                nach_port="Gi1/0/2",
            ),
            Cable(
                kabel_nr="KAB-0003",
                typ="LC-LC",
                laenge_m=15,
                farbe="gelb",
                von_device_id=switch.id,
                von_port="Te1/0/1",
                nach_device_id=fw.id,
                nach_port="Port1",
            ),
            Cable(
                kabel_nr="KAB-0004",
                typ="LC-LC",
                laenge_m=15,
                farbe="gelb",
                von_device_id=fw.id,
                von_port="Port2",
                nach_device_id=storage.id,
                nach_port="e0a",
            ),
            Cable(
                kabel_nr="KAB-0005",
                typ="DAC",
                laenge_m=2,
                farbe="grau",
                von_device_id=srv1.id,
                von_port="eth1",
                nach_device_id=switch.id,
                nach_port="Gi1/0/3",
            ),
            Cable(
                kabel_nr="KAB-0006",
                typ="Cat7",
                laenge_m=20,
                farbe="gruen",
                von_device_id=switch.id,
                von_port="Gi1/0/24",
                nach_device_id=srv2.id,
                nach_port="eth1",
            ),
            Cable(
                kabel_nr="KAB-0007",
                typ="Strom-C13",
                laenge_m=2,
                farbe="schwarz",
                von_device_id=pdu_a.id,
                von_port="Out1",
                nach_device_id=srv1.id,
                nach_port="PSU1",
            ),
            Cable(
                kabel_nr="KAB-0008",
                typ="Strom-C13",
                laenge_m=2,
                farbe="schwarz",
                von_device_id=pdu_a.id,
                von_port="Out2",
                nach_device_id=srv2.id,
                nach_port="PSU1",
            ),
            Cable(
                kabel_nr="KAB-0009",
                typ="Strom-C19",
                laenge_m=2,
                farbe="schwarz",
                von_device_id=pdu_a.id,
                von_port="Out3",
                nach_device_id=switch.id,
                nach_port="PSU1",
            ),
        ]
        db.add_all(cables)
        await db.flush()

        # 5. PDU Outlets
        outlets = [
            PduOutlet(
                pdu_id=pdu_a.id,
                outlet_name="Out1",
                phase="L1",
                steckdosentyp="C13",
                max_watt=2500,
                schaltbar=True,
                connected_device_id=srv1.id,
                connected_port="PSU1",
            ),
            PduOutlet(
                pdu_id=pdu_a.id,
                outlet_name="Out2",
                phase="L2",
                steckdosentyp="C13",
                max_watt=2500,
                schaltbar=True,
                connected_device_id=srv2.id,
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
        ]
        db.add_all(outlets)
        await db.flush()

        await db.commit()
        print(
            f"Seed erfolgreich: 2 Racks, {len(devices)} Devices, {len(cables)} Cables, {len(outlets)} PDU Outlets"
        )


if __name__ == "__main__":
    asyncio.run(main())
