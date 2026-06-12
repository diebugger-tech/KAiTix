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

![Landingpage](docs/screenshots/Landingpage.png)
*Landingpage — Serverraum-Infrastruktur. Dokumentiert & Simuliert.*

![Rack-Ansicht](docs/screenshots/Rack-Ansicht.png)
*Rechenzentrum Racks — Detaillierte Ansicht der Hardware, Rack-Belegung und PDU-Steckdosen*

![Topologie 3D](docs/screenshots/Topologie%203D.png)
*Topologie 3D — Interaktive 3D-Orbit-Ansicht mit Raycasting (klickbaren Geräten) und gebogenen 3D-Kabeln (Bezier Curves) zur rack-übergreifenden Visualisierung*

![USV-Auslegungsplanung](docs/screenshots/USV-Auslegungsplanung%20.png)
*USV-Auslegungsplanung — N+1 Simulator für Batterie- und Stromausfall-Szenarien*

![Runbook Orchestrator Planer](docs/screenshots/Runbook%20Orchestrator%20Planer%20.png)
*Runbook Orchestrator — Drag & Drop Planer für Shutdown- und Startup-Sequenzen*

![E-Plan Stromlaufplan](docs/screenshots/E-Plan.png)
*E-Plan — Dynamisch generierter allpoliger Stromlaufplan mit PDF-Export*

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
* **Detail-Dimensionierung:** Korrekte Hochvolt-Strangspannungen und Entladeschluss-Faktoren für reale Kabel- und Sicherungsdimensionierung bei Ausfall-Szenarien.
* **Phase Optimizer Sprint:** `phase_optimizer.py` als Wrapper über `PhaseBalancer`
* **Neue Endpoints:** `POST /api/v1/power/phase/optimize/{rack_id}` und `/apply`
* **Frontend:** Imbalance-Badge, Optimizer-Button, Dropdown-Warn-Icon

### 5. Predictive Analytics & Konsistenz-Validierung
* **Konsistenz-Validator:** Erkennt vollautomatisch logische Doku-Fehler wie U-Slot-Überlappungen, fehlende Phasen-Zuordnungen für Stromverbraucher und Netzwerk-Port-Doppelbelegungen.
* **Kaskadierende Ausfälle (Blast Radius):** Was passiert, wenn ein Core-Switch oder eine PDU ausfällt?
* **Redundanz-Check:** Erkennung isolierter oder stromloser Server sowie mitgerissener VMs und betroffener Runbook-Sequenzen.

### 6. EPLAN CSV Import & Kabeltyp-Mapping
* **Kabelimport:** EPLAN-Kabelverbindungslisten komfortabel per CSV hochladen.
* **Spaltenzuordnung:** Flexibler Parser mit dynamischem Spaltenmapping und automatischer Normierung freier Kabeltypen (z. B. `LWL-LC` zu standardisierten Enum-Werten wie `LC-LC`).

### 7. Kabellisten-Export
* **Multi-Format-Export:** Download der Verkabelungsliste als CSV, XLSX (via `openpyxl`) oder ODS (via `odfpy`).

### 8. Stromlaufplan & Topologie
* **Grafische Darstellung:** Interaktiver 2D-SVG Topologie-Graph zur rack-übergreifenden Visualisierung **sowie eine 3D-Orbit-Ansicht (three.js)** für komplexe RZ-Standorte.
* **Allpoliger Stromlaufplan:** Darstellung der PDU- und USV-Verbindungspfade als SVG mit direktem PDF-Export. Normgerecht gezeichnet mit 4-poligen Leistungsschaltern (MCCB), voreilenden Neutralleitern zur Vermeidung von Sternpunktverschiebungen und korrekter DC-Batterieabsicherung.

### 9. UX & Interface Design
* **Slate & Emerald Dark Theme:** KAiTix nutzt eine hochkontrastige, augenschonende "Slate & Emerald" Farbpalette, die speziell auf die Anforderungen in dunklen RZ-Umgebungen und auf maximale Lesbarkeit bei dichten Datentabellen und Metriken ausgelegt ist.
* **Effiziente Filter:** Schnelle 2-Wege-Synchronisation von Standort-, Reihen- und Rack-Filtern zum sofortigen Wechseln zwischen Rechenzentren.
* **Virtuelle Maschinen & Topology UI:** Umfassend überarbeitete Sidebar-Ansichten und Suchfunktionen für schnelle Navigation.

### 10. Referenz & Lernbereich
* **IPv6 Referenz:** Integriertes Cheat-Sheet für das IPv6-Design (VLAN-Mapping, ULAs, IID-Berechnung), direkt abrufbar aus der Navigation.


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
* **Frontend:** Svelte 5, Vite, Vanilla JS (kein TypeScript), CSS, Three.js (für 3D-Visualisierung)
* **Deployment:** Docker, Docker Compose, Nginx

---

## Installationsanleitung

### VARIANTE A — Container (Empfohlen)

Mit Podman/Docker müssen Sie **weder Python noch Node noch MySQL lokal installieren**.
Alle Abhängigkeiten werden automatisch im Container installiert:

* Das **`Containerfile`** installiert Python 3, Node 22, nginx und baut Backend + Frontend.
* **`compose.yml`** zieht das MySQL-8-Image, baut das App-Image, wendet die Migrationen an
  und lädt beim allerersten Start automatisch Demo-Daten (nur in eine leere DB).

#### Einzige Voraussetzung

Auf einem frischen System wird **nur die Container-Engine** benötigt — sie ist das einzige,
was sich nicht selbst installieren kann. Einmalig unter Ubuntu / Debian:

```bash
sudo apt install -y podman docker-compose
```
*(Alternativ Docker Desktop. Podman wird empfohlen: rootless, kein privilegierter Daemon.)*

#### Starten in 3 Befehlen

> [!TIP]
> Jeden Befehl **einzeln** kopieren. Die Zeilen sind bewusst kommentarfrei, damit das
> Einfügen in zsh/bash sauber durchläuft (zsh meldet sonst `command not found: #`).

**1. Repository klonen**
```bash
git clone https://github.com/diebugger-tech/KAiTix.git
cd KAiTix
```

**2. Umgebungsvariablen kopieren** (Defaults reichen für den Erststart)
```bash
cp .env.example .env
```

**3. Stack bauen & starten** (rootless empfohlen; alternativ `docker compose up --build`)
```bash
podman compose up --build
```
> KAiTix nutzt ab sofort eine **robuste Single-Image-Architektur** (Multi-Stage Static Build). Backend (FastAPI) und Frontend (SvelteKit) laufen im selben Container und werden gemeinsam über uvicorn (Port 8003 intern) ausgeliefert. Das reduziert Overhead und verhindert Sync-Probleme zwischen mehreren Containern.

Danach ist die Anwendung im Browser erreichbar unter: **http://localhost:8080**

> [!IMPORTANT]
> Im Browser **`http://localhost:8080`** öffnen. **Nicht** `0.0.0.0` und **nicht** die
> internen Ports `:3000` (Frontend) oder `:8003` (Backend) — das sind containerinterne
> Adressen, die der Browser nicht erreicht (`ERR_CONNECTION_REFUSED`). Alles läuft
> gebündelt über Port **8080**.

> [!NOTE]
> Beim **ersten** Start werden automatisch Demo-Daten geladen (Racks, Geräte, VMs,
> Runbooks). Das passiert nur, solange die Datenbank leer ist — bestehende Daten werden
> nie überschrieben. Abschaltbar via `SEED_DEMO_DATA=false` in der `.env`.

**Nützliche Befehle** (jeweils einzeln einfügen):

| Befehl | Wirkung |
|---|---|
| `podman compose down` | Stoppen (Daten bleiben im Volume erhalten) |
| `podman compose down -v` | Stoppen **und** Datenbank-Volume löschen (Reset) |
| `podman compose logs -f` | Logs live verfolgen |
| `podman compose watch` | Auto-Rebuild bei Quelländerungen (Entwicklung) |

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

   > **Hinweis für Ubuntu 24.04+ / Debian 12+:** Aufgrund von PEP 668 muss ein virtuelles Environment angelegt werden. Systemweises `pip install` wird blockiert.

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Datenbank-Migrationen ausführen (Alembic)**
   ```bash
   alembic upgrade head
   ```

4. **Node.js 20+ installieren (falls noch nicht vorhanden)**

   > **Hinweis für Ubuntu / Debian:** Node.js ist nicht im Standard-Repository enthalten. Verwenden Sie NodeSource:

   ```bash
   curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
   sudo apt-get install -y nodejs
   ```

5. **Frontend einrichten & starten**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   *(Das Svelte5-Frontend läuft standardmäßig unter http://localhost:5175)*

6. **Backend starten (in einem separaten Terminal)**
   ```bash
   # Zurück im Hauptverzeichnis
   source .venv/bin/activate
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
