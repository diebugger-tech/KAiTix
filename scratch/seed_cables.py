"""Seed realistic data center cables into KAiTix via API.

Usage: python3 scratch/seed_cables.py
Uses stdlib urllib — no external dependencies needed.
"""

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_URL = "http://127.0.0.1:8003/api/v1"

# Devices in DB (from seed/init):
#   srv-web-01 (id=3), sw-core-01 (id=4)
SRV_WEB = 3
SW_CORE = 4

CABLES = [
    # ── LWL Backbone OM4 (Multimode, Switch↔Switch) ──
    {
        "kabel_nr": "KAB-0003",
        "typ": "LC-LC",
        "laenge_m": 15.00,
        "farbe": "Erika-Violett",
        "von_device_id": SW_CORE,
        "von_port": "Eth1/1",
        "nach_device_id": SW_CORE,
        "nach_port": "Eth1/2",
        "bemerkung": "LWL Backbone OM4 — Core-Switch Uplink A",
    },
    {
        "kabel_nr": "KAB-0004",
        "typ": "LC-LC",
        "laenge_m": 12.00,
        "farbe": "Erika-Violett",
        "von_device_id": SW_CORE,
        "von_port": "Eth1/3",
        "nach_device_id": SW_CORE,
        "nach_port": "Eth1/4",
        "bemerkung": "LWL Backbone OM4 — Core-Switch Uplink B",
    },
    {
        "kabel_nr": "KAB-0005",
        "typ": "LC-LC",
        "laenge_m": 8.00,
        "farbe": "Erika-Violett",
        "von_device_id": SW_CORE,
        "von_port": "Eth1/5",
        "nach_device_id": SW_CORE,
        "nach_port": "Eth1/6",
        "bemerkung": "LWL Backbone OM4 — SAN Fabric A",
    },
    {
        "kabel_nr": "KAB-0006",
        "typ": "LC-LC",
        "laenge_m": 10.00,
        "farbe": "Erika-Violett",
        "von_device_id": SW_CORE,
        "von_port": "Eth1/7",
        "nach_device_id": SW_CORE,
        "nach_port": "Eth1/8",
        "bemerkung": "LWL Backbone OM4 — SAN Fabric B",
    },
    # ── LWL Breakout (MTP→LC, Patchpanel↔Switch) ──
    {
        "kabel_nr": "KAB-0007",
        "typ": "LC-LC",
        "laenge_m": 5.00,
        "farbe": "Gelb",
        "von_device_id": SW_CORE,
        "von_port": "Eth2/1",
        "nach_device_id": SRV_WEB,
        "nach_port": "eth1",
        "bemerkung": "LWL Breakout OS2 — Server WAN-Anbindung",
    },
    {
        "kabel_nr": "KAB-0008",
        "typ": "LC-LC",
        "laenge_m": 7.00,
        "farbe": "Gelb",
        "von_device_id": SW_CORE,
        "von_port": "Eth2/2",
        "nach_device_id": SRV_WEB,
        "nach_port": "eth2",
        "bemerkung": "LWL Breakout OS2 — Server Backup-Netz",
    },
    {
        "kabel_nr": "KAB-0009",
        "typ": "LC-LC",
        "laenge_m": 20.00,
        "farbe": "Gelb",
        "von_device_id": SW_CORE,
        "von_port": "Eth2/3",
        "nach_device_id": SRV_WEB,
        "nach_port": "eth3",
        "bemerkung": "LWL Backbone OS2 — DCI Interconnect A",
    },
    {
        "kabel_nr": "KAB-0010",
        "typ": "LC-LC",
        "laenge_m": 18.00,
        "farbe": "Gelb",
        "von_device_id": SW_CORE,
        "von_port": "Eth2/4",
        "nach_device_id": SRV_WEB,
        "nach_port": "eth4",
        "bemerkung": "LWL Backbone OS2 — DCI Interconnect B",
    },
    # ── Kupfer RJ-45 Cat6A (Server↔Switch, Management) ──
    {
        "kabel_nr": "KAB-0011",
        "typ": "Cat6A",
        "laenge_m": 2.00,
        "farbe": "Blau",
        "von_device_id": SRV_WEB,
        "von_port": "eth0",
        "nach_device_id": SW_CORE,
        "nach_port": "Gi1/0/1",
        "bemerkung": "Cat6A Management LAN — IPMI/iLO",
    },
    {
        "kabel_nr": "KAB-0012",
        "typ": "Cat6A",
        "laenge_m": 3.00,
        "farbe": "Blau",
        "von_device_id": SRV_WEB,
        "von_port": "eth5",
        "nach_device_id": SW_CORE,
        "nach_port": "Gi1/0/2",
        "bemerkung": "Cat6A Prod-LAN — Webserver",
    },
    {
        "kabel_nr": "KAB-0013",
        "typ": "Cat6A",
        "laenge_m": 1.50,
        "farbe": "Blau",
        "von_device_id": SRV_WEB,
        "von_port": "eth6",
        "nach_device_id": SW_CORE,
        "nach_port": "Gi1/0/3",
        "bemerkung": "Cat6A Monitoring-Netz",
    },
    {
        "kabel_nr": "KAB-0014",
        "typ": "Cat6A",
        "laenge_m": 2.50,
        "farbe": "Blau",
        "von_device_id": SRV_WEB,
        "von_port": "eth7",
        "nach_device_id": SW_CORE,
        "nach_port": "Gi1/0/4",
        "bemerkung": "Cat6A Backup-Netz",
    },
    {
        "kabel_nr": "KAB-0015",
        "typ": "Cat6A",
        "laenge_m": 2.00,
        "farbe": "Blau",
        "von_device_id": SRV_WEB,
        "von_port": "KVM",
        "nach_device_id": SW_CORE,
        "nach_port": "Gi1/0/5",
        "bemerkung": "Cat6A KVM-over-IP",
    },
    {
        "kabel_nr": "KAB-0016",
        "typ": "Cat6A",
        "laenge_m": 3.00,
        "farbe": "Blau",
        "von_device_id": SRV_WEB,
        "von_port": "IPMI",
        "nach_device_id": SW_CORE,
        "nach_port": "Gi1/0/6",
        "bemerkung": "Cat6A Out-of-Band Management",
    },
    # ── Kupfer Cat7 S/FTP (SAN, rot) ──
    {
        "kabel_nr": "KAB-0017",
        "typ": "Cat7",
        "laenge_m": 3.00,
        "farbe": "Rot",
        "von_device_id": SRV_WEB,
        "von_port": "san0",
        "nach_device_id": SW_CORE,
        "nach_port": "Gi2/0/1",
        "bemerkung": "Cat7 SAN S/FTP — Storage Fabric A",
    },
    {
        "kabel_nr": "KAB-0018",
        "typ": "Cat7",
        "laenge_m": 5.00,
        "farbe": "Rot",
        "von_device_id": SRV_WEB,
        "von_port": "san1",
        "nach_device_id": SW_CORE,
        "nach_port": "Gi2/0/2",
        "bemerkung": "Cat7 SAN S/FTP — Storage Fabric B",
    },
    {
        "kabel_nr": "KAB-0019",
        "typ": "Cat7",
        "laenge_m": 2.00,
        "farbe": "Rot",
        "von_device_id": SRV_WEB,
        "von_port": "san2",
        "nach_device_id": SW_CORE,
        "nach_port": "Gi2/0/3",
        "bemerkung": "Cat7 SAN S/FTP — Replication",
    },
    # ── DAC (Direct Attach Copper, Top-of-Rack) ──
    {
        "kabel_nr": "KAB-0020",
        "typ": "DAC",
        "laenge_m": 1.00,
        "farbe": None,
        "von_device_id": SRV_WEB,
        "von_port": "SFP+1",
        "nach_device_id": SW_CORE,
        "nach_port": "Te1/0/1",
        "bemerkung": "DAC 10G SFP+ — ToR Server A",
    },
    {
        "kabel_nr": "KAB-0021",
        "typ": "DAC",
        "laenge_m": 2.00,
        "farbe": None,
        "von_device_id": SRV_WEB,
        "von_port": "SFP+2",
        "nach_device_id": SW_CORE,
        "nach_port": "Te1/0/2",
        "bemerkung": "DAC 10G SFP+ — ToR Server B",
    },
    {
        "kabel_nr": "KAB-0022",
        "typ": "DAC",
        "laenge_m": 3.00,
        "farbe": None,
        "von_device_id": SRV_WEB,
        "von_port": "QSFP1",
        "nach_device_id": SW_CORE,
        "nach_port": "Fo1/0/1",
        "bemerkung": "DAC 40G QSFP+ — Backbone Trunk",
    },
    # ── Strom C13 (Server↔PDU) ──
    {
        "kabel_nr": "KAB-0023",
        "typ": "Strom-C13",
        "laenge_m": 1.50,
        "farbe": "Schwarz",
        "von_device_id": SRV_WEB,
        "von_port": "PSU1",
        "nach_device_id": None,
        "nach_port": "PDU-A Slot 1",
        "bemerkung": "Strom C13/C14 — PDU-A Phase L1",
    },
    {
        "kabel_nr": "KAB-0024",
        "typ": "Strom-C13",
        "laenge_m": 1.50,
        "farbe": "Schwarz",
        "von_device_id": SRV_WEB,
        "von_port": "PSU2",
        "nach_device_id": None,
        "nach_port": "PDU-B Slot 1",
        "bemerkung": "Strom C13/C14 — PDU-B Phase L2 (Redundanz)",
    },
    {
        "kabel_nr": "KAB-0025",
        "typ": "Strom-C13",
        "laenge_m": 2.00,
        "farbe": "Schwarz",
        "von_device_id": SW_CORE,
        "von_port": "PSU1",
        "nach_device_id": None,
        "nach_port": "PDU-A Slot 3",
        "bemerkung": "Strom C13/C14 — Core-Switch PDU-A",
    },
    {
        "kabel_nr": "KAB-0026",
        "typ": "Strom-C13",
        "laenge_m": 2.00,
        "farbe": "Schwarz",
        "von_device_id": SW_CORE,
        "von_port": "PSU2",
        "nach_device_id": None,
        "nach_port": "PDU-B Slot 3",
        "bemerkung": "Strom C13/C14 — Core-Switch PDU-B",
    },
    # ── Strom C19 (Blade-Chassis, höhere Last) ──
    {
        "kabel_nr": "KAB-0027",
        "typ": "Strom-C19",
        "laenge_m": 2.00,
        "farbe": "Grau",
        "von_device_id": SRV_WEB,
        "von_port": "Chassis-PSU1",
        "nach_device_id": None,
        "nach_port": "PDU-A Slot 5",
        "bemerkung": "Strom C19/C20 — Blade-Chassis Hochstrom L1",
    },
    {
        "kabel_nr": "KAB-0028",
        "typ": "Strom-C19",
        "laenge_m": 2.00,
        "farbe": "Grau",
        "von_device_id": SRV_WEB,
        "von_port": "Chassis-PSU2",
        "nach_device_id": None,
        "nach_port": "PDU-B Slot 5",
        "bemerkung": "Strom C19/C20 — Blade-Chassis Hochstrom L2",
    },
    # ── Erdung (Grün-Gelb, Potenzialausgleich) ──
    {
        "kabel_nr": "KAB-0029",
        "typ": "sonstige",
        "laenge_m": 2.00,
        "farbe": "Grün-Gelb",
        "von_device_id": None,
        "von_port": "RACK-01 Erdschiene",
        "nach_device_id": None,
        "nach_port": "PA-Schiene Hauptverteiler",
        "bemerkung": "Erdung RACK-01 — Potenzialausgleich 16mm²",
    },
    {
        "kabel_nr": "KAB-0030",
        "typ": "sonstige",
        "laenge_m": 2.50,
        "farbe": "Grün-Gelb",
        "von_device_id": None,
        "von_port": "RACK-02 Erdschiene",
        "nach_device_id": None,
        "nach_port": "PA-Schiene Hauptverteiler",
        "bemerkung": "Erdung RACK-02 — Potenzialausgleich 16mm²",
    },
]


def api_get(path: str) -> list | dict:
    req = Request(f"{BASE_URL}{path}", method="GET")
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def api_post(path: str, data: dict) -> tuple[int, str]:
    body = json.dumps(data).encode()
    req = Request(
        f"{BASE_URL}{path}",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode()
    except HTTPError as e:
        return e.code, e.read().decode()


def main():
    existing = {c["kabel_nr"] for c in api_get("/cables/")}
    print(f"Vorhandene Kabel: {len(existing)}")

    created = 0
    skipped = 0
    errors = 0

    for cable in CABLES:
        if cable["kabel_nr"] in existing:
            print(f"  SKIP  {cable['kabel_nr']} (existiert)")
            skipped += 1
            continue

        status, body = api_post("/cables/", cable)
        if status == 201:
            print(
                f"  OK    {cable['kabel_nr']} ({cable['typ']}, {cable.get('farbe', '—')})"
            )
            created += 1
        else:
            print(f"  ERR   {cable['kabel_nr']}: {status} — {body[:120]}")
            errors += 1

    print(f"\nFertig: {created} erstellt, {skipped} übersprungen, {errors} Fehler")
    print(f"Gesamt Kabel in DB: {len(existing) + created}")


if __name__ == "__main__":
    main()
