"""Seed-Script: Erzeugt vollständige Showcase-Testdaten für KAiTix.

Dieses Skript leert die Datenbank komplett und fügt 4 Racks, Wöhrle USVs,
komplexe Verkabelung (Strom, LAN, SAN), virtuelle Maschinen und Runbooks ein,
um KAiTix auf GitHub eindrucksvoll präsentieren zu können.
"""

import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine, Base
from app.domains.hardware.models import Rack, Device, PduOutlet, VirtualMachine
from app.domains.cabling.models import Cable, CableStrand, Interface
from app.domains.power.models import UsvUnit, UsvModule, UsvSimulationEvent
from app.domains.runbooks.models import Runbook, RunbookLayer, RunbookDevice

async def main():
    # 1. Clean Slate: Wipe and recreate all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    print("Datenbank geleert und Schema neu erstellt.")

    async with AsyncSessionLocal() as db:
        # 2. Racks (4 Racks for different purposes)
        rack_netzwerk = Rack(name="RACK-NET-01", standort="RZ1-ReiheA", hoehe_u=42, breite_mm=800, hersteller="Rittal", bemerkung="Core Netzwerk & Routing")
        rack_app = Rack(name="RACK-APP-01", standort="RZ1-ReiheA", hoehe_u=47, breite_mm=600, hersteller="Rittal", bemerkung="Compute Nodes")
        rack_db = Rack(name="RACK-DB-01", standort="RZ1-ReiheA", hoehe_u=47, breite_mm=600, hersteller="Rittal", bemerkung="High-Density Database")
        rack_storage = Rack(name="RACK-SAN-01", standort="RZ1-ReiheB", hoehe_u=42, breite_mm=800, hersteller="Rittal", bemerkung="Storage & Backup")
        
        db.add_all([rack_netzwerk, rack_app, rack_db, rack_storage])
        await db.flush()

        # 3. Power (PDUs & Wöhrle USV)
        # RACK-NET-01 PDUs
        pdu_net_a = Device(hostname="PDU-NET-A", typ="pdu", hersteller="Kentix", modell="SmartPDU", rack_id=rack_netzwerk.id, u_position=0, phase="L1", anschlussleistung_watt=0)
        pdu_net_b = Device(hostname="PDU-NET-B", typ="pdu", hersteller="Kentix", modell="SmartPDU", rack_id=rack_netzwerk.id, u_position=0, phase="L2", anschlussleistung_watt=0)
        
        # RACK-APP-01 PDUs (Intentionally imbalanced to test Phase Balancer)
        pdu_app_a = Device(hostname="PDU-APP-A", typ="pdu", hersteller="Kentix", modell="SmartPDU", rack_id=rack_app.id, u_position=0, phase="L1", anschlussleistung_watt=0)
        pdu_app_b = Device(hostname="PDU-APP-B", typ="pdu", hersteller="Kentix", modell="SmartPDU", rack_id=rack_app.id, u_position=0, phase="L1", anschlussleistung_watt=0) # Also L1!
        
        db.add_all([pdu_net_a, pdu_net_b, pdu_app_a, pdu_app_b])
        await db.flush()
        
        # Wöhrle USV System in RACK-APP-01
        usv1 = UsvUnit(bezeichnung="Wöhrle WP2-R 40kW Haupt-USV", hersteller="Wöhrle SVS", rack_id=rack_app.id, max_kw=40.0)
        db.add(usv1)
        await db.flush()
        
        # Add 3 Modules to USV (30kW total, N+1 ready if load < 20kW)
        usv_mod1 = UsvModule(usv_unit_id=usv1.id, slot=1, leistung_kw=10.0, status="aktiv")
        usv_mod2 = UsvModule(usv_unit_id=usv1.id, slot=2, leistung_kw=10.0, status="aktiv")
        usv_mod3 = UsvModule(usv_unit_id=usv1.id, slot=3, leistung_kw=10.0, status="reserve")
        db.add_all([usv_mod1, usv_mod2, usv_mod3])
        await db.flush()

        import json
        from datetime import datetime, timezone

        # Add a realistic simulation event showing Peukert battery curve calculation
        sim_event = UsvSimulationEvent(
            usv_unit_id=usv1.id,
            timestamp=datetime.now(timezone.utc),
            event_type="simulation",
            severity="info",
            description="Kalkulation der Batterie-Entladekurve (Peukert 1.15, 60Ah)",
            snapshot_json=json.dumps({
                "peukert_k": 1.15,
                "nominal_capacity_ah": 60,
                "temperature_c": 22,
                "aging_factor_pct": 98,
                "expected_runtime_minutes": 45.5,
                "total_load_kw": 18.5,
                "n1_safe": True,
                "notes": "Optimale Entladekurve berechnet. Reservekapazität ausreichend für geplanten Shutdown."
            })
        )
        db.add(sim_event)
        await db.flush()

        # 4. Networking Devices (RACK-NET-01)
        fw1 = Device(hostname="fw-core-01", typ="firewall", hersteller="Fortinet", modell="FortiGate 100F", rack_id=rack_netzwerk.id, u_position=40, u_hoehe=1, tdp_watt=120, phase="L1")
        sw_core1 = Device(hostname="sw-core-01", typ="switch", hersteller="Cisco", modell="Nexus 93180", rack_id=rack_netzwerk.id, u_position=38, u_hoehe=1, tdp_watt=400, phase="L2")
        sw_core2 = Device(hostname="sw-core-02", typ="switch", hersteller="Cisco", modell="Nexus 93180", rack_id=rack_netzwerk.id, u_position=36, u_hoehe=1, tdp_watt=400, phase="L3")
        db.add_all([fw1, sw_core1, sw_core2])
        await db.flush()

        # 5. Compute Servers (RACK-APP-01) - Imbalanced on phases
        servers_app = []
        for i in range(1, 7):
            # Put most on L1 to create imbalance
            phase = "L1" if i <= 4 else ("L2" if i == 5 else "L3")
            srv = Device(hostname=f"srv-compute-{i:02d}", typ="server", hersteller="Dell", modell="PowerEdge R750", rack_id=rack_app.id, u_position=i*2, u_hoehe=2, tdp_watt=850, phase=phase)
            servers_app.append(srv)
        db.add_all(servers_app)
        
        # 6. Database Servers (RACK-DB-01)
        srv_db_master = Device(hostname="srv-db-master", typ="server", hersteller="HPE", modell="ProLiant DL380", rack_id=rack_db.id, u_position=10, u_hoehe=2, tdp_watt=1200, phase="L2")
        srv_db_slave = Device(hostname="srv-db-slave", typ="server", hersteller="HPE", modell="ProLiant DL380", rack_id=rack_db.id, u_position=12, u_hoehe=2, tdp_watt=1200, phase="L3")
        db.add_all([srv_db_master, srv_db_slave])
        
        # 7. Storage (RACK-SAN-01)
        san_controller = Device(hostname="san-ctrl-01", typ="storage", hersteller="PureStorage", modell="FlashArray//X", rack_id=rack_storage.id, u_position=20, u_hoehe=3, tdp_watt=1500, phase="L1")
        db.add(san_controller)
        await db.flush()

        # 8. Virtual Machines (Microservice Architecture)
        vm_db = VirtualMachine(name="vm-pg-cluster", host_device_id=srv_db_master.id, hypervisor_typ="vmware", dienst="PostgreSQL 16", ip_adresse="10.0.1.10", shutdown_priority=1, responsible="DBA")
        db.add(vm_db)
        await db.flush()
        
        vm_redis = VirtualMachine(name="vm-redis-cache", host_device_id=servers_app[0].id, hypervisor_typ="vmware", dienst="Redis Cluster", ip_adresse="10.0.1.20", shutdown_priority=2, depends_on_vm_id=vm_db.id)
        db.add(vm_redis)
        await db.flush()
        
        vm_backend_api = VirtualMachine(name="vm-backend-api", host_device_id=servers_app[1].id, hypervisor_typ="vmware", dienst="FastAPI Core", ip_adresse="10.0.1.30", shutdown_priority=3, depends_on_vm_id=vm_redis.id)
        vm_backend_worker = VirtualMachine(name="vm-backend-worker", host_device_id=servers_app[2].id, hypervisor_typ="vmware", dienst="Celery Workers", ip_adresse="10.0.1.31", shutdown_priority=4, depends_on_vm_id=vm_redis.id)
        db.add_all([vm_backend_api, vm_backend_worker])
        await db.flush()
        
        vm_frontend = VirtualMachine(name="vm-frontend-ssr", host_device_id=servers_app[3].id, hypervisor_typ="vmware", dienst="SvelteKit SSR", ip_adresse="10.0.1.40", shutdown_priority=5, depends_on_vm_id=vm_backend_api.id)
        vm_nginx = VirtualMachine(name="vm-nginx-ingress", host_device_id=servers_app[4].id, hypervisor_typ="vmware", dienst="NGINX Reverse Proxy", ip_adresse="10.0.1.50", shutdown_priority=6, depends_on_vm_id=vm_frontend.id)
        db.add_all([vm_frontend, vm_nginx])
        await db.flush()

        # 9. Cables
        # Connect servers to core switch (LAN - Blau)
        cables = []
        for i, srv in enumerate(servers_app):
            c = Cable(kabel_nr=f"LAN-{100+i}", typ="Cat6A", farbe="Blau", laenge_m=5.0, von_device_id=srv.id, von_port="eth0", nach_device_id=sw_core1.id, nach_port=f"Gi1/0/{i+1}")
            cables.append(c)
        
        # Connect DB servers to SAN (Fibre - Erika-Violett)
        cables.append(Cable(kabel_nr="SAN-001", typ="LC-LC", farbe="Erika-Violett", laenge_m=10.0, von_device_id=srv_db_master.id, von_port="fc1", nach_device_id=san_controller.id, nach_port="port1"))
        cables.append(Cable(kabel_nr="SAN-002", typ="LC-LC", farbe="Erika-Violett", laenge_m=10.0, von_device_id=srv_db_slave.id, von_port="fc1", nach_device_id=san_controller.id, nach_port="port2"))
        db.add_all(cables)
        await db.flush()

        # 10. Runbooks
        rb_shutdown = Runbook(name="Geplanter RZ Shutdown", typ="shutdown", beschreibung="Sicheres Herunterfahren der gesamten KAiTix Showcase Umgebung inkl. Storage und Netzwerk.")
        db.add(rb_shutdown)
        await db.flush()
        
        l_web = RunbookLayer(runbook_id=rb_shutdown.id, name="Web & Ingress", position=1, markdown_note="Zuerst Traffic von außen stoppen (NGINX).")
        l_app = RunbookLayer(runbook_id=rb_shutdown.id, name="Applikationen & Worker", position=2)
        l_db = RunbookLayer(runbook_id=rb_shutdown.id, name="Datenbanken & Caches", position=3)
        l_infra = RunbookLayer(runbook_id=rb_shutdown.id, name="Storage & Core Netz", position=4)
        db.add_all([l_web, l_app, l_db, l_infra])
        await db.flush()
        
        # Devices in Runbook
        db.add(RunbookDevice(runbook_id=rb_shutdown.id, layer_id=l_web.id, vm_id=vm_nginx.id, position=1, delay_seconds=10))
        db.add(RunbookDevice(runbook_id=rb_shutdown.id, layer_id=l_web.id, vm_id=vm_frontend.id, position=2, delay_seconds=10))
        
        db.add(RunbookDevice(runbook_id=rb_shutdown.id, layer_id=l_app.id, vm_id=vm_backend_api.id, position=1, delay_seconds=30))
        db.add(RunbookDevice(runbook_id=rb_shutdown.id, layer_id=l_app.id, vm_id=vm_backend_worker.id, position=2, delay_seconds=30))
        
        db.add(RunbookDevice(runbook_id=rb_shutdown.id, layer_id=l_db.id, vm_id=vm_redis.id, position=1, delay_seconds=60))
        db.add(RunbookDevice(runbook_id=rb_shutdown.id, layer_id=l_db.id, vm_id=vm_db.id, position=2, delay_seconds=120, responsible="DBA"))
        
        db.add(RunbookDevice(runbook_id=rb_shutdown.id, layer_id=l_infra.id, device_id=srv_db_master.id, position=1))
        db.add(RunbookDevice(runbook_id=rb_shutdown.id, layer_id=l_infra.id, device_id=san_controller.id, position=2, note="SAN Controller sauber herunterfahren", delay_seconds=300))
        db.add(RunbookDevice(runbook_id=rb_shutdown.id, layer_id=l_infra.id, device_id=sw_core1.id, position=3))

        await db.commit()
        print("Showcase Testdaten erfolgreich in die Datenbank geschrieben!")

if __name__ == "__main__":
    asyncio.run(main())
