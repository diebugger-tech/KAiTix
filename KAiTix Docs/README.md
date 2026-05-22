# ServerFlow

Standalone Serverraum-Verwaltung: Kabelliste, Server-Inventar, USV-Berechnung, Kentix-Integration.

## Stack
- Python 3.11+
- SQLAlchemy 2.x sync + PyMySQL
- Typer + Rich (CLI)
- httpx (Kentix REST)
- MySQL 8+

## Install

```bash
pip install typer sqlalchemy pymysql rich python-dotenv httpx
```

## Setup

```bash
# .env anlegen
cp .env.example .env
# DB-Schema einspielen
mysql -u root -p < db/schema.sql
# CLI testen
python cli/cli.py --help
```

## Schnellstart

```bash
# Rack anlegen
python cli/cli.py rack add RACK-01 "Serverraum EG"

# USV anlegen (Wöhrle 40kW Schrank)
python cli/cli.py usv add-unit "Wöhrle 40kW" 40.0 1

# 4 Module à 10 kW eintragen
python cli/cli.py usv add-module 1 1 10.0
python cli/cli.py usv add-module 1 2 10.0
python cli/cli.py usv add-module 1 3 10.0
python cli/cli.py usv add-module 1 4 10.0

# Server anlegen
python cli/cli.py device add srv-01 --typ server --ip 192.168.1.10 --rack 1 --watt 400 --phase L1

# USV berechnen
python cli/cli.py usv calc 1

# Phasenverteilung prüfen
python cli/cli.py phase-check 1

# Kentix Poller starten
python integrations/kentix.py daemon

# Kentix einmalig abfragen
python integrations/kentix.py poll
```

## Projektstruktur

```
serverflow/
├── db/
│   └── schema.sql          # MySQL Schema
├── cli/
│   └── cli.py              # Typer CLI (alle Commands)
├── integrations/
│   └── kentix.py           # Kentix REST Poller
├── .env                    # Credentials (nicht ins Git!)
└── README.md
```
