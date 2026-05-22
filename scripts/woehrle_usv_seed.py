#!/usr/bin/env python3
"""
Wöhrle SVS USV-Modelle in hardware_types.json eintragen.
Aufruf: python scripts/woehrle_usv_seed.py
"""

import json

path = "/home/andreas/Projekte/aktiv/KAiTix/data/hardware_types.json"
with open(path) as f:
    data = json.load(f)

next_id = max(h["id"] for h in data) + 1

woehrle = [
    {
        "id": next_id,
        "name": "Wöhrle SVS WP2-R 10kW Modul",
        "kategorie": "usv",
        "hersteller": "Wöhrle SVS",
        "modell": "WP2-R 10kW",
        "u_hoehe": 3,
        "breite_mm": None,
        "tiefe_mm": None,
        "min_rack_hoehe": 0,
        "tdp_watt": None,
        "psu_count": None,
        "psu_nennwatt": None,
        "leistung_kw": 10.0,
        "n1_faehig": True,
        "bemerkung": "Leistungsmodul für WP2-R Schrank, N+1 fähig, hot-swap",
    },
    {
        "id": next_id + 1,
        "name": "Wöhrle SVS WP2-R 20kW Modul",
        "kategorie": "usv",
        "hersteller": "Wöhrle SVS",
        "modell": "WP2-R 20kW",
        "u_hoehe": 3,
        "breite_mm": None,
        "tiefe_mm": None,
        "min_rack_hoehe": 0,
        "tdp_watt": None,
        "psu_count": None,
        "psu_nennwatt": None,
        "leistung_kw": 20.0,
        "n1_faehig": True,
        "bemerkung": "Leistungsmodul für WP2-R Schrank, N+1 fähig, hot-swap",
    },
    {
        "id": next_id + 2,
        "name": "Wöhrle SVS WP2-R 40kW Schrank",
        "kategorie": "usv",
        "hersteller": "Wöhrle SVS",
        "modell": "WP2-R 40kW",
        "u_hoehe": 20,
        "breite_mm": 600,
        "tiefe_mm": 800,
        "min_rack_hoehe": 0,
        "tdp_watt": None,
        "psu_count": None,
        "psu_nennwatt": None,
        "leistung_kw": 40.0,
        "n1_faehig": True,
        "bemerkung": "Modularer USV-Schrank, bis 4× 10kW Module, N+1, 97.6% Wirkungsgrad",
    },
    {
        "id": next_id + 3,
        "name": "Wöhrle SVS WP2-R 80kW Schrank",
        "kategorie": "usv",
        "hersteller": "Wöhrle SVS",
        "modell": "WP2-R 80kW",
        "u_hoehe": 30,
        "breite_mm": 600,
        "tiefe_mm": 800,
        "min_rack_hoehe": 0,
        "tdp_watt": None,
        "psu_count": None,
        "psu_nennwatt": None,
        "leistung_kw": 80.0,
        "n1_faehig": True,
        "bemerkung": "Modularer USV-Schrank, bis 4× 20kW Module, N+1, DARA-Architektur",
    },
]

data.extend(woehrle)
with open(path, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"OK — {len(woehrle)} Wöhrle-Modelle hinzugefügt, IDs {next_id}–{next_id + 3}")
for w in woehrle:
    print(f"  ID={w['id']} {w['name']}")
