"""Seed PDU devices and outlets into KAiTix via API.

Usage: python3 scratch/seed_pdus.py
Uses stdlib urllib — no external dependencies needed.
"""

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_URL = "http://127.0.0.1:8003/api/v1"

RACK_01 = 3
SRV_WEB = 3
SW_CORE = 4


def api_get(path: str):
    req = Request(f"{BASE_URL}{path}", method="GET")
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def api_post(path: str, data: dict) -> tuple[int, str]:
    body = json.dumps(data).encode()
    url = f"{BASE_URL}{path}"
    req = Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode()
    except HTTPError as e:
        # Handle 307 redirect manually
        if e.code == 307 and e.headers.get("Location"):
            redirect_url = e.headers["Location"]
            if not redirect_url.startswith("http"):
                redirect_url = f"http://127.0.0.1:8003{redirect_url}"
            req2 = Request(
                redirect_url,
                data=body,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            try:
                with urlopen(req2, timeout=10) as resp2:
                    return resp2.status, resp2.read().decode()
            except HTTPError as e2:
                return e2.code, e2.read().decode()
        return e.code, e.read().decode()


def main():
    existing = {d["hostname"] for d in api_get("/pdus/")}
    print(f"Vorhandene PDUs: {len(existing)}")

    pdus = [
        {
            "hostname": "PDU-A-R01",
            "typ": "pdu",
            "hersteller": "Kentix",
            "modell": "SmartPDU 42HE",
            "seriennummer": "KNT-PDU-2024-001",
            "rack_id": RACK_01,
            "u_position": None,
            "u_hoehe": 0,
            "strom_typ": "3-phasig",
            "spannung_v": 400,
            "anschlussleistung_a": 32.0,
            "anschluss_stecker": "CEE-32A-3P",
            "bemerkung": "PDU A — Ersteinspeisung, 3-phasig 32A, CEE-32A-3P (rot)",
        },
        {
            "hostname": "PDU-B-R01",
            "typ": "pdu",
            "hersteller": "Kentix",
            "modell": "SmartPDU 42HE",
            "seriennummer": "KNT-PDU-2024-002",
            "rack_id": RACK_01,
            "u_position": None,
            "u_hoehe": 0,
            "strom_typ": "3-phasig",
            "spannung_v": 400,
            "anschlussleistung_a": 32.0,
            "anschluss_stecker": "CEE-32A-3P",
            "bemerkung": "PDU B — Redundanteinspeisung, 3-phasig 32A, CEE-32A-3P (rot)",
        },
    ]

    created_pdus = []
    for pdu in pdus:
        if pdu["hostname"] in existing:
            print(f"  SKIP  {pdu['hostname']} (existiert)")
            # Get existing PDU ID
            all_pdus = api_get("/pdus/")
            for p in all_pdus:
                if p["hostname"] == pdu["hostname"]:
                    created_pdus.append(p)
                    break
            continue

        status, body = api_post("/pdus/", pdu)
        if status == 201:
            data = json.loads(body)
            created_pdus.append(data)
            print(f"  OK    {pdu['hostname']} (PDU #{data['id']})")
        else:
            print(f"  ERR   {pdu['hostname']}: {status} — {body[:120]}")

    # Create outlets for each PDU
    for pdu_data in created_pdus:
        pdu_id = pdu_data["id"]
        existing_outlets = {
            o["outlet_name"] for o in api_get(f"/pdus/{pdu_id}/outlets")
        }

        # Phase distribution: L1, L2, L3 alternating
        phases = ["L1", "L2", "L3"]
        outlet_configs = []
        for i in range(1, 13):
            phase = phases[(i - 1) % 3]
            typ = "C19" if i <= 6 else "C13"
            max_w = 3680 if typ == "C19" else 2300
            outlet_configs.append(
                {
                    "outlet_name": f"Outlet-{i:02d}",
                    "phase": phase,
                    "steckdosentyp": typ,
                    "max_watt": max_w,
                    "schaltbar": True,
                }
            )

        # Connect some outlets to devices
        connections = {
            "Outlet-01": (SRV_WEB, "PSU1"),
            "Outlet-02": (SW_CORE, "PSU1"),
            "Outlet-04": (SRV_WEB, "PSU2"),
            "Outlet-05": (SW_CORE, "PSU2"),
        }

        created = 0
        skipped = 0
        for cfg in outlet_configs:
            if cfg["outlet_name"] in existing_outlets:
                skipped += 1
                continue

            data = {"pdu_id": pdu_id, **cfg}
            if cfg["outlet_name"] in connections:
                dev_id, port = connections[cfg["outlet_name"]]
                data["connected_device_id"] = dev_id
                data["connected_port"] = port

            status, body = api_post(f"/pdus/{pdu_id}/outlets/", data)
            if status == 201:
                created += 1
            else:
                print(f"    ERR {cfg['outlet_name']}: {status} — {body[:80]}")

        print(
            f"  {pdu_data['hostname']}: {created} Outlets erstellt, {skipped} übersprungen"
        )

    # Create 3-phase power cables for PDUs
    existing_cables = {c["kabel_nr"] for c in api_get("/cables/")}
    pdu_cables = [
        {
            "kabel_nr": "KAB-0031",
            "typ": "Strom-CEE-32A-3P",
            "laenge_m": 5.00,
            "farbe": "Rot",
            "von_device_id": created_pdus[0]["id"] if len(created_pdus) > 0 else None,
            "von_port": "CEE-32A Eingang",
            "nach_device_id": None,
            "nach_port": "Verteiler 32A L1+L2+L3",
            "bemerkung": "3-phasig 32A CEE — PDU-A Zuleitung",
        },
        {
            "kabel_nr": "KAB-0032",
            "typ": "Strom-CEE-32A-3P",
            "laenge_m": 5.00,
            "farbe": "Rot",
            "von_device_id": created_pdus[1]["id"] if len(created_pdus) > 1 else None,
            "von_port": "CEE-32A Eingang",
            "nach_device_id": None,
            "nach_port": "Verteiler 32A L1+L2+L3",
            "bemerkung": "3-phasig 32A CEE — PDU-B Zuleitung",
        },
    ]

    for cable in pdu_cables:
        if cable["kabel_nr"] in existing_cables:
            print(f"  SKIP  {cable['kabel_nr']} (Kabel existiert)")
            continue
        status, body = api_post("/cables/", cable)
        if status == 201:
            print(f"  OK    {cable['kabel_nr']} ({cable['typ']})")
        else:
            print(f"  ERR   {cable['kabel_nr']}: {status} — {body[:80]}")

    print("\nFertig!")


if __name__ == "__main__":
    main()
