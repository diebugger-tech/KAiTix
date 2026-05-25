"""Seed-Script: Erzeugt realistische Testdaten für KAiTix.

Aufruf: python scripts/seed_testdata.py
"""

import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.domains.hardware.models import Rack, DeviceDependency, Device, PduOutlet, VirtualMachine
from app.domains.cabling.models import Cable, CableStrand, Interface
from app.domains.power.models import UsvUnit, UsvModule, UsvSimulationEvent
from app.domains.runbooks.models import Runbook, RunbookLayer, RunbookDevice, RunbookExecution, RunbookExecutionStep

async def main():
    async with AsyncSessionLocal() as db:
        # Check and delete existing test data to make the script idempotent
        # Delete runbooks with matching names
        rb_names = ["Geplanter Shutdown EG", "Notfall-Startup EG"]
        for rb_name in rb_names:
            q = await db.execute(select(Runbook).where(Runbook.name == rb_name))
            rb = q.scalars().first()
            if rb:
                await db.delete(rb)
        
        # Clear specific VMs
        vm_names = ["vm-db-master", "vm-db-slave", "vm-app-backend", "vm-app-worker", "vm-web-nginx", "vm-monitoring"]
        for vm_name in vm_names:
            q = await db.execute(select(VirtualMachine).where(VirtualMachine.name == vm_name))
            vm = q.scalars().first()
            if vm:
                await db.delete(vm)
                
        # Clear specific devices
        dev_hostnames = ["sw-core-01", "sw-access-01", "srv-db-01", "srv-db-02", "srv-app-01", "srv-app-02", "srv-web-01", "kentix-01"]
        for host in dev_hostnames:
            q = await db.execute(select(Device).where(Device.hostname == host))
            dev = q.scalars().first()
            if dev:
                await db.delete(dev)
                
        # Clear specific Racks
        rack_names = ["RACK-01", "RACK-02"]
        for rname in rack_names:
            q = await db.execute(select(Rack).where(Rack.name == rname))
            rack = q.scalars().first()
            if rack:
                await db.delete(rack)
                
        await db.commit()
        
        # 1. Racks
        rack1 = Rack(
            name="RACK-01", 
            standort="Serverraum EG", 
            hoehe_u=42, 
            breite_mm=600, 
            hersteller="Rittal", 
            modell="VX IT 42HE 600mm",
            bemerkung="Hauptverteiler-Rack"
        )
        rack2 = Rack(
            name="RACK-02", 
            standort="Serverraum EG", 
            hoehe_u=47, 
            breite_mm=800, 
            hersteller="Rittal", 
            modell="TS IT 47HE 800mm",
            bemerkung="Applikations-Rack"
        )
        db.add_all([rack1, rack2])
        await db.flush()
        
        # 2. Devices
        dev_sw_core = Device(
            hostname="sw-core-01", 
            typ="switch", 
            hersteller="Cisco", 
            modell="Catalyst 9500", 
            rack_id=rack1.id, 
            u_position=1, 
            u_hoehe=1, 
            anschlussleistung_watt=150, 
            phase="L1"
        )
        dev_sw_access = Device(
            hostname="sw-access-01", 
            typ="switch", 
            hersteller="Cisco", 
            modell="Catalyst 9300", 
            rack_id=rack1.id, 
            u_position=2, 
            u_hoehe=1, 
            anschlussleistung_watt=80, 
            phase="L2"
        )
        dev_srv_db1 = Device(
            hostname="srv-db-01", 
            typ="server", 
            hersteller="Dell", 
            modell="PowerEdge R750", 
            rack_id=rack1.id, 
            u_position=10, 
            u_hoehe=2, 
            anschlussleistung_watt=400, 
            phase="L1"
        )
        dev_srv_db2 = Device(
            hostname="srv-db-02", 
            typ="server", 
            hersteller="Dell", 
            modell="PowerEdge R750", 
            rack_id=rack1.id, 
            u_position=12, 
            u_hoehe=2, 
            anschlussleistung_watt=400, 
            phase="L1"
        )
        dev_srv_app1 = Device(
            hostname="srv-app-01", 
            typ="server", 
            hersteller="HP", 
            modell="ProLiant DL360", 
            rack_id=rack1.id, 
            u_position=20, 
            u_hoehe=1, 
            anschlussleistung_watt=350, 
            phase="L2"
        )
        dev_srv_app2 = Device(
            hostname="srv-app-02", 
            typ="server", 
            hersteller="HP", 
            modell="ProLiant DL360", 
            rack_id=rack1.id, 
            u_position=22, 
            u_hoehe=1, 
            anschlussleistung_watt=350, 
            phase="L2"
        )
        dev_srv_web = Device(
            hostname="srv-web-01", 
            typ="server", 
            hersteller="HP", 
            modell="ProLiant DL360", 
            rack_id=rack2.id, 
            u_position=5, 
            u_hoehe=1, 
            anschlussleistung_watt=250, 
            phase="L3"
        )
        dev_kentix = Device(
            hostname="kentix-01", 
            typ="kentix_raconode", 
            hersteller="Kentix", 
            modell="RACOONODE", 
            rack_id=rack1.id, 
            u_position=42, 
            u_hoehe=1, 
            ip_adresse="192.168.1.200"
        )
        
        db.add_all([dev_sw_core, dev_sw_access, dev_srv_db1, dev_srv_db2, dev_srv_app1, dev_srv_app2, dev_srv_web, dev_kentix])
        await db.flush()
        
        # 3. VMs
        vm_db_master = VirtualMachine(
            name="vm-db-master", 
            host_device_id=dev_srv_db1.id, 
            hypervisor_typ="kvm", 
            dienst="MySQL Master", 
            ip_adresse="192.168.10.10", 
            shutdown_priority=1,
            responsible="DBA Team"
        )
        db.add(vm_db_master)
        await db.flush()
        
        vm_db_slave = VirtualMachine(
            name="vm-db-slave", 
            host_device_id=dev_srv_db2.id, 
            hypervisor_typ="kvm", 
            dienst="MySQL Slave", 
            ip_adresse="192.168.10.11", 
            shutdown_priority=2, 
            depends_on_vm_id=vm_db_master.id,
            responsible="DBA Team"
        )
        vm_app_backend = VirtualMachine(
            name="vm-app-backend", 
            host_device_id=dev_srv_app1.id, 
            hypervisor_typ="kvm", 
            dienst="FastAPI Backend", 
            ip_adresse="192.168.10.20", 
            shutdown_priority=3, 
            depends_on_vm_id=vm_db_master.id,
            responsible="Backend Team"
        )
        vm_monitoring = VirtualMachine(
            name="vm-monitoring", 
            host_device_id=dev_srv_app1.id, 
            hypervisor_typ="kvm", 
            dienst="Prometheus+Grafana", 
            ip_adresse="192.168.10.40", 
            shutdown_priority=6, 
            depends_on_vm_id=vm_db_master.id,
            responsible="Ops Team"
        )
        
        db.add_all([vm_db_slave, vm_app_backend, vm_monitoring])
        await db.flush()
        
        vm_app_worker = VirtualMachine(
            name="vm-app-worker", 
            host_device_id=dev_srv_app2.id, 
            hypervisor_typ="kvm", 
            dienst="Celery Worker", 
            ip_adresse="192.168.10.21", 
            shutdown_priority=4, 
            depends_on_vm_id=vm_app_backend.id,
            responsible="Backend Team"
        )
        vm_web_nginx = VirtualMachine(
            name="vm-web-nginx", 
            host_device_id=dev_srv_web.id, 
            hypervisor_typ="kvm", 
            dienst="Nginx Proxy", 
            ip_adresse="192.168.10.30", 
            shutdown_priority=5, 
            depends_on_vm_id=vm_app_backend.id,
            responsible="Ops Team"
        )
        
        db.add_all([vm_app_worker, vm_web_nginx])
        await db.flush()
        
        # 4. Runbook 1: Geplanter Shutdown EG
        rb1 = Runbook(
            name="Geplanter Shutdown EG", 
            typ="shutdown", 
            beschreibung="Sicherer Shutdown des EG Serverraums."
        )
        db.add(rb1)
        await db.flush()
        
        l1 = RunbookLayer(runbook_id=rb1.id, name="Web-Tier", position=1)
        l2 = RunbookLayer(runbook_id=rb1.id, name="App-Tier", position=2)
        l3 = RunbookLayer(runbook_id=rb1.id, name="Datenbank-Tier", position=3)
        l4 = RunbookLayer(runbook_id=rb1.id, name="Netzwerk", position=4)
        
        db.add_all([l1, l2, l3, l4])
        await db.flush()
        
        # Layer 1 Devices
        rd1 = RunbookDevice(runbook_id=rb1.id, layer_id=l1.id, vm_id=vm_web_nginx.id, position=1)
        rd2 = RunbookDevice(runbook_id=rb1.id, layer_id=l1.id, device_id=dev_srv_web.id, position=2)
        
        # Layer 2 Devices
        rd3 = RunbookDevice(runbook_id=rb1.id, layer_id=l2.id, vm_id=vm_app_backend.id, position=1)
        rd4 = RunbookDevice(runbook_id=rb1.id, layer_id=l2.id, vm_id=vm_app_worker.id, position=2)
        rd5 = RunbookDevice(runbook_id=rb1.id, layer_id=l2.id, device_id=dev_srv_app1.id, position=3)
        rd6 = RunbookDevice(runbook_id=rb1.id, layer_id=l2.id, device_id=dev_srv_app2.id, position=4)
        
        # Layer 3 Devices
        rd7 = RunbookDevice(runbook_id=rb1.id, layer_id=l3.id, vm_id=vm_db_master.id, position=1)
        rd8 = RunbookDevice(runbook_id=rb1.id, layer_id=l3.id, vm_id=vm_db_slave.id, position=2)
        rd9 = RunbookDevice(runbook_id=rb1.id, layer_id=l3.id, device_id=dev_srv_db1.id, position=3)
        rd10 = RunbookDevice(runbook_id=rb1.id, layer_id=l3.id, device_id=dev_srv_db2.id, position=4)
        
        # Layer 4 Devices
        rd11 = RunbookDevice(runbook_id=rb1.id, layer_id=l4.id, device_id=dev_sw_access.id, position=1)
        rd12 = RunbookDevice(runbook_id=rb1.id, layer_id=l4.id, device_id=dev_sw_core.id, position=2)
        
        db.add_all([rd1, rd2, rd3, rd4, rd5, rd6, rd7, rd8, rd9, rd10, rd11, rd12])
        await db.flush()
        
        # 5. Runbook 2: Notfall-Startup EG (Umkehrung von Runbook 1)
        rb2 = Runbook(
            name="Notfall-Startup EG", 
            typ="startup", 
            beschreibung="Sicherer Startup des EG Serverraums.", 
            generated_from_id=rb1.id
        )
        db.add(rb2)
        await db.flush()
        
        # Reversed layers
        ls1 = RunbookLayer(runbook_id=rb2.id, name="Netzwerk", position=1)
        ls2 = RunbookLayer(runbook_id=rb2.id, name="Datenbank-Tier", position=2)
        ls3 = RunbookLayer(runbook_id=rb2.id, name="App-Tier", position=3)
        ls4 = RunbookLayer(runbook_id=rb2.id, name="Web-Tier", position=4)
        
        db.add_all([ls1, ls2, ls3, ls4])
        await db.flush()
        
        # ls1 Netzwerk Devices
        rds1 = RunbookDevice(runbook_id=rb2.id, layer_id=ls1.id, device_id=dev_sw_access.id, position=1)
        rds2 = RunbookDevice(runbook_id=rb2.id, layer_id=ls1.id, device_id=dev_sw_core.id, position=2)
        
        # ls2 Datenbank Devices
        rds3 = RunbookDevice(runbook_id=rb2.id, layer_id=ls2.id, vm_id=vm_db_master.id, position=1)
        rds4 = RunbookDevice(runbook_id=rb2.id, layer_id=ls2.id, vm_id=vm_db_slave.id, position=2)
        rds5 = RunbookDevice(runbook_id=rb2.id, layer_id=ls2.id, device_id=dev_srv_db1.id, position=3)
        rds6 = RunbookDevice(runbook_id=rb2.id, layer_id=ls2.id, device_id=dev_srv_db2.id, position=4)
        
        # ls3 App Devices
        rds7 = RunbookDevice(runbook_id=rb2.id, layer_id=ls3.id, vm_id=vm_app_backend.id, position=1)
        rds8 = RunbookDevice(runbook_id=rb2.id, layer_id=ls3.id, vm_id=vm_app_worker.id, position=2)
        rds9 = RunbookDevice(runbook_id=rb2.id, layer_id=ls3.id, device_id=dev_srv_app1.id, position=3)
        rds10 = RunbookDevice(runbook_id=rb2.id, layer_id=ls3.id, device_id=dev_srv_app2.id, position=4)
        
        # ls4 Web Devices
        rds11 = RunbookDevice(runbook_id=rb2.id, layer_id=ls4.id, vm_id=vm_web_nginx.id, position=1)
        rds12 = RunbookDevice(runbook_id=rb2.id, layer_id=ls4.id, device_id=dev_srv_web.id, position=2)
        
        db.add_all([rds1, rds2, rds3, rds4, rds5, rds6, rds7, rds8, rds9, rds10, rds11, rds12])
        await db.flush()
        
        await db.commit()
        print("Realistische Testdaten erfolgreich initialisiert!")

if __name__ == "__main__":
    asyncio.run(main())
