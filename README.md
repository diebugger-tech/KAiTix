# KAiTix ServerFlow

**Rechenzentrum-Dokumentation & Showroom-Tool für IT-Dienstleister**

[![License: AGPL-v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![SvelteKit 5](https://img.shields.io/badge/SvelteKit-5.0-ff3e00.svg)](https://svelte.dev/)

KAiTix dokumentiert physische RZ-Infrastruktur — Racks, Server, PDUs, Kabel, USV — und macht sie im Kunden-Meeting präsentierbar. Kein Monitoring, keine Live-Daten, keine Komplexität. Eintragen, zeigen, exportieren.

> **Typischer Workflow:** Techniker pflegt Kundendaten ein → öffnet KAiTix beim Meeting → „Das ist Ihr Rack." → PDF-Export per E-Mail.

---

## Schnellstart (Docker — empfohlen)

Läuft auf **Windows, macOS und Linux** ohne weitere Abhängigkeiten.

```bash
git clone https://github.com/diebugger-tech/KAiTix.git
cd KAiTix
cp .env.example .env
docker compose up
```

Danach im Browser: **http://localhost**

### Voraussetzung: Docker Desktop

| Betriebssystem | Download |
|---|---|
| Windows 10/11 | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| macOS | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| Ubuntu / Debian | `sudo apt install docker.io docker-compose-plugin` |
| NixOS | Deklarativ via `virtualisation.docker.enable = true` |

---

## Was KAiTix kann

### Rack-Dokumentation
Geräte (Server, Switches, Firewalls, PDUs, Storage) mit U-Position, Hersteller, Modell, Seriennummer und TDP erfassen. PDU-Steckdosenbelegung pro Phase (L1/L2/L3) dokumentieren.

### Kabelmanagement & EPLAN-Import
Kabelliste mit Typ, Länge, Farbe und Quelle/Ziel. EPLAN CSV-Import mit Live-Vorschau. Export als XLSX, ODS oder CSV.

### Stromlaufplan & Topologie
Allpoliger Stromlaufplan (DIN EN 61082-1) als SVG. Topologie-Graph mit Geräten und Kabelverbindungen. **PDF-Export** direkt aus der Oberfläche.

### USV-Simulation
N+1 Redundanz-Kalkulation auf Basis dokumentierter Nennleistungen. MBS-Bypass-Simulation: welche Server werden bei Phasenausfall stromlos?

---

## Kein Docker — Entwicklung lokal

### Linux & NixOS
```bash
nix-shell              # oder: python3 -m venv .venv && source .venv/bin/activate
make install           # Python-Abhängigkeiten
make migrate-apply     # Datenbank einrichten
cd frontend && npm install && cd ..
make dev-all           # Backend :8003 + Frontend :5175
```

### macOS
```bash
brew install python@3.12 node mysql pkg-config openssl
python3 -m venv .venv && source .venv/bin/activate
make install && make migrate-apply
cd frontend && npm install && cd ..
make dev-all
```

### Windows
Ohne Docker empfehlen wir **WSL2 + Ubuntu**, dann wie Linux oben.  
Alternativ: Docker Desktop (siehe Schnellstart).

---

## Demo-Daten laden

```bash
# Mit aktivem .venv und laufender Datenbank:
PYTHONPATH=. python scratch/seed_demo_data.py
# → 2 Racks, 7 Geräte, 9 Kabel, 3 PDU-Outlets
```

---

## Makefile-Referenz

| Befehl | Beschreibung |
|---|---|
| `make dev` | Backend starten (Port 8003) |
| `make dev-frontend` | Frontend starten (Port 5175) |
| `make dev-all` | Backend + Frontend parallel |
| `make install` | Python-Abhängigkeiten installieren |
| `make test` | pytest ausführen |
| `make lint` | ruff + mypy |
| `make format` | ruff fix + format |
| `make migrate-create message="..."` | Alembic-Migration erstellen |
| `make migrate-apply` | Migrationen anwenden |
| `make clean` | Temporäre Dateien löschen |

---

## Stack

- **Backend:** FastAPI 0.110+, SQLAlchemy 2.0 (async), Alembic, MySQL 8
- **Frontend:** SvelteKit 5, TailwindCSS, Lucide Icons
- **Export:** openpyxl (XLSX), odfpy (ODS), SVG → PDF via Browser-Print
- **Deployment:** Docker Compose + nginx reverse proxy

---

## Lizenz

[AGPL-3.0](LICENSE) — freie Nutzung im eigenen Unternehmen. Modifikationen die als SaaS betrieben werden müssen unter gleicher Lizenz veröffentlicht werden.
