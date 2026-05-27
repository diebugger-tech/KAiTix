# KAiTix — Plan. Simulate. Document.

**Infrastruktur-Dokumentation & Showroom-Tool für Rechenzentrumsinfrastruktur**

[![License: AGPL-v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![Node: 20+](https://img.shields.io/badge/Node-20+-brightgreen.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Svelte 5](https://img.shields.io/badge/Svelte-5.0-ff3e00.svg)](https://svelte.dev/)
[![MySQL 8](https://img.shields.io/badge/MySQL-8.0-blue.svg)](https://www.mysql.com/)

KAiTix ist ein hochspezialisiertes Planungs-, Simulations- und Dokumentationswerkzeug für MSP-Techniker und IT-Teams. Es dient als Single Source of Truth für die visuelle Darstellung von Racks, PDU-Steckdosenbelegungen, Kabelverbindungen und USV-Dimensionierungen sowie für die Simulation von Ausfallszenarien (Blast Radius).

> [!NOTE]
> **Plan. Simulate. Document.**  
> KAiTix verzichtet bewusst auf Live-Monitoring (keine SNMP/API-Abfragen) oder Echtzeitdaten. Die Stärke von KAiTix liegt in der präzisen Modellierung und der Vorhersage von Was-wäre-wenn-Szenarien (z. B. kaskadierende Strom-/Netzwerkausfälle, Phasen-Ungleichgewicht oder USV-Redundanz).

---

## Screenshots

![Dashboard](docs/screenshots/dashboard.png)
*Dashboard — Übersicht aller Racks, Phasenauslastung und Schnellexport*

![Rack-Übersicht](docs/screenshots/racks-uebersicht.png)
*Rechenzentrum Racks — Standorte, Rack-Belegung und PDU-Steckdosen*

![Rack-Detail](docs/screenshots/racks-detail.png)
*Rack-Detail — U-Position, Gerättypen, PDU-Verkabelung*

![Topologie](docs/screenshots/topologie.png)
*Topologie — Netzwerk- und Stromverbindungen zwischen Racks, filterbar nach Kabeltyp*

![E-Plan Stromlaufplan](docs/screenshots/eplan-stromlaufplan-1.png)
*E-Plan — Allpoliger Stromlaufplan nach DIN EN 61082-1 mit PDF- und CAD-Export*

---

## Features & Funktionalitäten

### 1. Rack- & Geräte-Dokumentation
* **U-genaue Positionierung:** Geräte (Server, Switches, Firewalls, Kentix-Komponenten) mit präzisen U-Höhen, TDP-Werten und Seriennummern dokumentieren.
* **0U-PDU-Validierung:** Maximale PDU-Höhen- und Positionskontrolle (z. B. Ausschluss von 47HE-PDUs in 42HE-Racks; nur eine vertikale PDU pro Seite).

### 2. VM-Landschaft
* **Abhängigkeiten & Zuordnung:** Virtuelle Maschinen mit Host-Server-Zuordnung, Hypervisor-Typ und Abhängigkeitsgraph (`depends_on`).
* **Visualisierung:** Interaktives Graphen-Diagramm mit Bezier-Kurven. Hover-Effekt hebt direkte Vorgänger und Nachfolger hervor.

### 3. Runbook Orchestrator
* **Drag & Drop Planer:** Shutdown- und Startup-Sequenzen komfortabel via Weboberfläche in Layer einteilen.
* **Interaktives Protokoll:** Schritt-für-Schritt-Ausführung mit namentlichem Audit-Trail (Wer hat wann welchen Schritt abgehakt/zurückgenommen).
* **Startup auto-generiert:** Automatische Umkehrung eines Shutdown-Runbooks auf Knopfdruck.

### 4. USV-Simulation & Phasenlast-Berechnung
* **N+1 Dimensionierung:** Berechnung der minimalen Anzahl an USV- und Batteriemodulen, die für eine Autonomiezeit bei Phasenungleichgewicht (L1/L2/L3) erforderlich sind.
* **VDE Protokoll-Tab:** On-the-Fly Audit und Visualisierung von USV-Compliance-Status und Berechnungs-Historien direkt im Modal der Geräteansicht.
* **Phasenlasten:** Berechnung und Warnung bei Asymmetrie der Stromlasten über die drei Phasen (inklusive Phasen-Imbalance Widget).

### 5. Predictive Analytics: Blast Radius (Ausfall-Simulation)
* **Kaskadierende Ausfälle:** Was passiert, wenn ein Core-Switch oder eine PDU ausfällt?
* **Redundanz-Check:** Erkennung isolierter oder stromloser Server sowie mitgerissener VMs und betroffener Runbook-Sequenzen.

### 6. EPLAN CSV Import & Kabeltyp-Mapping
* **Kabelimport:** EPLAN-Kabelverbindungslisten komfortabel per CSV hochladen.
* **Spaltenzuordnung:** Flexibler Parser mit dynamischem Spaltenmapping und automatischer Normierung freier Kabeltypen (z. B. `LWL-LC` zu standardisierten Enum-Werten wie `LC-LC`).

### 7. Kabellisten-Export
* **Multi-Format-Export:** Download der Verkabelungsliste als CSV, XLSX (via `openpyxl`) oder ODS (via `odfpy`).

### 8. Stromlaufplan & Topologie
* **Grafische Darstellung:** Interaktiver D3.js/Cytoscape.js Topologie-Graph zur rack-übergreifenden Visualisierung.
* **Allpoliger Stromlaufplan:** Darstellung der PDU- und USV-Verbindungspfade als SVG mit direktem PDF-Export.

---

## Architektur & Design-Prinzipien

KAiTix folgt einem bewusst einfachen und fokussierten Design. Diese Prinzipien sind **nicht verhandelbar** — sie schützen das Tool vor unnötiger Komplexität.

- **Intranet-Only** — keine Cloud, keine externen APIs, läuft vollständig im lokalen Netzwerk. Keine Internet-Exponierung vorgesehen.
- **Single-User** — kein Auth-System, kein Session-Management, kein Multi-User. Gedacht für einen Techniker / Admin im gesicherten Intranet.
- **Kein Live-Monitoring** — KAiTix dokumentiert und simuliert, liest aber keine Echtzeit-Daten aus. Kein SNMP-Polling, kein Live-Dashboard, keine automatischen Aktionen.
- **Plan. Simulate. Document.** — nicht überwachen, nicht automatisieren. Werte kommen aus der Datenbank, nicht von Geräten.

> [!IMPORTANT]
> KI-Agenten und Entwickler: Bitte **keine** Auth-Middleware, Session-Management, Multi-User-Features oder Echtzeit-Polling-Komponenten einbauen. Das wäre ein Bug, kein Feature.

---

## Tech Stack

* **Backend:** FastAPI, SQLAlchemy 2.0 (Async), Alembic, MySQL 8 (aiomysql)
* **Frontend:** Svelte 5, Vite, Vanilla JS (kein TypeScript), CSS
* **Deployment:** Docker, Docker Compose, Nginx

---

## Installationsanleitung

### VARIANTE A — Docker (Empfohlen)

Mit Docker und Docker Compose müssen Sie Python, Node und MySQL nicht lokal installieren. Alles läuft in isolierten Containern.

#### Voraussetzungen
* Docker + Docker Compose installiert (z. B. über Docker Desktop)

#### Starten in 3 Befehlen
```bash
# 1. Repository klonen
git clone https://github.com/diebugger-tech/KAiTix.git
cd KAiTix

# 2. Umgebungsvariablen kopieren (ggf. anpassen)
cp .env.example .env

# 3. Docker Compose Stack starten
docker compose up    # oder
podman compose up    # Empfohlen bei KI-assistierter Entwicklung — läuft rootless ohne privilegierten Daemon
```

*Hinweis:* Podman läuft rootless (kein Root-Daemon) und ist die empfohlene Option für KI-assistierte Entwicklung sowie sicherheitskritische Umgebungen.

Danach ist die Anwendung im Browser erreichbar unter: **http://localhost**

---

### VARIANTE B — Manuelle Installation (Linux/Mac/Windows)

Falls Sie die Anwendung direkt auf Ihrem System installieren und ausführen möchten.

#### Voraussetzungen
* **Python 3.11+**
* **Node 20+**
* **MySQL 8+** (lokal installiert und konfiguriert)

#### Installationsschritte

1. **Umgebungsvariablen anlegen**
   ```bash
   cp .env.example .env
   ```
   *Wichtig:* Passen Sie `DATABASE_URL` in der `.env`-Datei an Ihre lokale MySQL-Datenbankverbindung an (z. B. `DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/kaitix`).

2. **Python-Abhängigkeiten installieren**
   ```bash
   pip install -r requirements.txt
   ```

3. **Datenbank-Migrationen ausführen (Alembic)**
   ```bash
   alembic upgrade head
   ```

4. **Frontend einrichten & starten**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   *(Das Svelte5-Frontend läuft standardmäßig unter http://localhost:5175)*

5. **Backend starten (in einem separaten Terminal)**
   ```bash
   # Zurück im Hauptverzeichnis
   uvicorn app.main:app --reload
   ```
   *(Das FastAPI-Backend läuft standardmäßig unter http://localhost:8003)*

---

## Demo-Daten laden (Seeding)

Um KAiTix mit Beispieldaten zu testen (2 Racks, 8 Geräte, 6 VMs, 2 Runbooks), führen Sie folgendes Skript aus:

```bash
# Mit aktivem venv und konfigurierten Datenbank-Zugangsdaten in .env:
PYTHONPATH=. python3 scripts/seed_testdata.py
```

---

## Makefile-Referenz (Lokale Entwicklung)

| Befehl | Beschreibung |
|---|---|
| `make dev` | Backend starten (Port 8003) |
| `make dev-frontend` | Frontend starten (Port 5175) |
| `make dev-all` | Backend + Frontend parallel starten |
| `make install` | Python-Abhängigkeiten installieren (in nix-shell) |
| `make test` | `pytest` ausführen |
| `make lint` | Code mit `ruff` und `mypy` prüfen |
| `make format` | Code mit `ruff` formatieren |
| `make migrate-create message="..."` | Neue Alembic-Datenbankmigration erstellen |
| `make migrate-apply` | Alembic-Migrationen auf Datenbank anwenden |
| `make clean` | Temporäre Dateien (Cache, Backups) entfernen |

---

## Lizenz

[AGPL-3.0](LICENSE) — Freie Nutzung im eigenen Unternehmen. Modifikationen, die als SaaS betrieben werden, müssen unter der gleichen Lizenz veröffentlicht werden.
