# AGENTS.md — KAiTix
> Globaler Agent-Context für das gesamte Projekt.
> Canonical Source: Projekt-Root (`/AGENTS.md`)
> Gelesen von: Claude Code, Goose, opencode, pydantic-deep

## Grundprinzip

- **KAiTix ist ein "Plan. Simulate. Document." Hardwaredokumentations- und Showroom-Tool** für Rechenzentrumsinfrastruktur
- **Produktziel**: Single Source of Truth für MSP-Techniker zur Planung, Ausfall-Simulation (Blast Radius) und visuellen Dokumentation.
- **Kein Multi-Tenant, kein Kunden-Login** — eine Instanz, ein Team, maximale Einfachheit
- **Kein Monitoring, keine Live-Daten** — keine SNMP-, API- oder Netzwerkanbindung an PDUs, Server oder Switches
- **Keine Echtzeitwerte** — KAiTix glänzt durch *Vorhersage und Simulation* (Was-wäre-wenn-Szenarien), nicht durch Polling-Loops oder Sensordaten.
- **Zweck**: Infrastruktur-Planung, Simulation, Dokumentation + visuelle Präsentation von Racks, Geräten, Kabeln, PDU-Steckdosen, USV-Dimensionierung
- **Kentix/Geräte**: Nur physische Installation dokumentieren (Modell, Seriennummer, Position, Anschlusswerte)
- **Simulationen**: Reine Berechnung auf Basis dokumentierter Daten (z.B. N+1 USV-Redundanz, kaskadierende Ausfälle), keine Live-Lastdaten

## Projekthistorie & Ursprung

- **ServerFlow** war der Vorgänger / die Basis von KAiTix (Typer CLI, synchrone SQLAlchemy, PyMySQL).
- **KAiTix** ist die vollständige asynchrone Neuentwicklung davon (FastAPI, async SQLAlchemy, Svelte 5, Alembic).
- Die ServerFlow-Dateien (`cli.py`, `kentix.py`, `schema.sql`, `Leistungsbeschreibung_USV.docx`) dienen als wertvolles Referenzmaterial für Domänenwissen (z. B. USV-Berechnung, Kentix-Integration, Schema-Struktur).

### Design-Prinzipien (nicht verhandelbar)

- **Intranet-Only** — keine Cloud, keine externen APIs, läuft vollständig im lokalen Netzwerk. Keine Internet-Exponierung vorgesehen.
- **Single-User** — kein Auth-System, kein Session-Management, kein Multi-User. Gedacht für einen Techniker / Admin im gesicherten Intranet.
- **Kein Live-Monitoring** — KAiTix dokumentiert und simuliert, liest aber keine Echtzeit-Daten aus. Kein SNMP-Polling, kein Live-Dashboard, keine automatischen Aktionen.
- **Plan. Simulate. Document.** — nicht überwachen, nicht automatisieren. Werte kommen aus der Datenbank, nicht von Geräten.

**HARDREGEL FÜR AGENTEN:** Folgende Features sind **niemals** einzubauen:
- ❌ Auth-Middleware (JWT, OAuth, Basic-Auth, SSO)
- ❌ Session-Management (Cookies, Server-Side Sessions)
- ❌ Multi-User / Rollen / Permissions
- ❌ WebSockets oder Polling-Loops
- ❌ Externe API-Calls zur Laufzeit (SNMP, REST-Abfragen an Geräte)
- ❌ Live-Dashboards mit Auto-Refresh

**Showroom-Workflow:**
1. Techniker pflegt Kundendaten in KAiTix
2. Rack-Diagramm + Topologie-Graph beim Kunden-Meeting öffnen
3. PDF-Export mit Logo per E-Mail an Kunden

**Kerndatenmodell:**
- Racks enthalten Geräte an definierten U-Positionen
- Geräte haben Interfaces (RJ45, LC/LWL, SFP+, SC, IPMI, FC usw.)
- Interfaces sind über Kabel verbunden — mit Quelle (Von-Gerät + Port) und Ziel (Nach-Gerät + Port)
- Verbindungen können rack-übergreifend sein
- PDUs dokumentieren Steckdosenbelegung pro Phase (L1/L2/L3)

**Kerndatenmodell:**
- Racks enthalten Geräte an definierten U-Positionen
- Geräte haben Interfaces (RJ45, LC/LWL, SFP+, SC, IPMI, FC usw.)
- Interfaces sind über Kabel verbunden — mit Quelle (Von-Gerät + Port) und Ziel (Nach-Gerät + Port)
- Verbindungen können rack-übergreifend sein
- PDUs dokumentieren Steckdosenbelegung pro Phase (L1/L2/L3)

## Architektur-Entscheidungen (ADR)

### ADR — Livedaten-Mustererkennung ist KEIN KAiTix-Feature
- **Entscheidung:** Mustererkennung auf Livedaten (Messverläufe, ML, Predictive) lebt im separaten Projekt CabellistPro, dokumentiert in `future.md` (gitignored).
- **Begründung:** NUR DOKU. KAiTix sammelt per Design keine Zeitreihen (`kentix_readings` aus ServerFlow bewusst entfallen). Der Schritt Simulation → Livedaten ist technisch klein — genau deshalb ist die Grenze eine bewusste Entscheidung, keine technische Hürde.
- **Konsequenz:** KAiTix-seitig nur deterministische, erklärbare Simulation auf dokumentierter Konfig. Kein Live-Feed, kein Polling, kein externer Schreibzugriff.

## Modell-Routing-Tabelle

| Modell | Aufgabe | Begründung | Kontextgröße |
|---|---|---|---|
| GLM-5 | Multi-file Refactoring, Backend + Frontend | Starke Architekturübersicht, gute Code-Generierung über mehrere Dateien | 128K |
| DeepSeek V3 | Single-file Fixes, Bugfixes | Präzise lokale Änderungen, hohe Code-Verständnis auf Dateiebene | 64K |
| Gemini 2.5 Flash | Lange Svelte-Dateien, Frontend-Reviews | Sehr großes Kontextfenster für lange UI-Komponenten | 1M |
| Claude Sonnet | Planung, Architektur, Prompt-Engineering | Hervorragendes Reasoning, ADRs, komplexe Designentscheidungen | 200K |

## Commit-Konventionen

Wir nutzen **Conventional Commits** mit folgenden Typen:

| Typ | Verwendung | Beispiel |
|---|---|---|
| `feat` | Neue Funktionalität | `feat(api): add user authentication endpoint` |
| `fix` | Bugfix | `fix(db): resolve connection pool exhaustion` |
| `chore` | Wartung, Build, CI | `chore(deps): update sqlalchemy to 2.0.30` |
| `refactor` | Code-Restrukturierung ohne Verhaltensänderung | `refactor(models): extract base class` |
| `docs` | Dokumentation | `docs(readme): update setup instructions` |
| `test` | Tests hinzufügen/ändern | `test(auth): add login flow tests` |
| `style` | Formatierung (keine Logikänderung) | `style(api): ruff formatting` |

Regeln:
- Imperativ, Präsens: "add", nicht "added"
- Kurze Überschrift (<72 Zeichen)
- Body optional, aber bei komplexen Änderungen erforderlich
- Referenziere Issues: `fixes #123`

## Pre-Task Checkliste

Vor jedem Agenten-Task:

1. **Branch prüfen** — `make check-branch` ausführen
2. **Git Status prüfen** — `git status` — keine uncommitteten Änderungen vom vorherigen Task
3. **Aktueller Branch** — Auf `feature/agent-<taskname>` oder `main` (nur für Docs)
4. **Commit vor Start** — Falls lokale Änderungen existieren: `git add -A && git commit -m "chore: pre-agent checkpoint"`
5. **Keine ungetesteten Frontend-Änderungen** — Agenten dürfen keine Svelte/JS-Änderungen deployen ohne `npm run build` zu bestehen
6. **Test-Check** — `pytest -v` muss vor dem Task grün sein (außer der Task ist das Fixen eines bekannten Bugs)

## Verbotene Operationen (Hard Constraints)

```
❌ DB-Migrationen ohne menschliches Review erstellen oder anwenden
❌ Force-Push auf `main` oder `dev`
❌ Secrets in Commits (Keys, Tokens, Passwörter)
❌ pip install außerhalb nix-shell (kein globales pip auf NixOS)
❌ make install außerhalb nix-shell aufrufen
❌ Bestehende Migrations-Dateien ändern (Alembic: einmal generiert = immutable)
❌ Frontend-Dateien direkt auf Prod deployen ohne Build-Check
❌ Beim Updaten der README.md oder anderer Dokumentationen bleiben bestehende Bilder und Screenshot-Links zwingend unangetastet auf GitHub. (Agenten dürfen keine existierenden Bilder/Screenshots in `docs/screenshots/` modifizieren oder deren Referenzen ungefragt löschen)
❌ `git reset --hard` ohne vorheriges Backup
❌ Große Binary-Dateien (>1MB) ins Repo committen
❌ .env oder .key-Dateien committen
✅ Erlaubt: innerhalb nix-shell -> python3 -m pip install -r requirements.txt
✅ Erlaubt: pipx install / pipx inject für CLI-Tools
```

## Stack-spezifische Hinweise (Python / FastAPI)

- **Async überall**: FastAPI-Endpunkte und SQLAlchemy-Operationen müssen `async` sein
- **Typisierung**: 100 % Type Hints, Pydantic V2 Models für Request/Response
- **SQLAlchemy 2.x**: Neue `select()`-Syntax, kein Legacy-Query-Stil
- **Dependency Injection**: FastAPI `Depends()` für DB-Sessions, Auth, etc.
- **Fehlerbehandlung**: Zentrale Exception Handler, niemals Stacktraces an Client senden
- **Alembic**:
  - alembic immer als `python3 -m alembic` aus nix-shell + aktiviertem .venv aufrufen
  - `ALEMBIC_SYNC_MODE=1` setzen wenn nötig
  - Workflow: nix-shell -> .venv aktivieren -> python3 -m alembic
  - Migrationen immer reviewen vor `make migrate-apply`
- **Commit-Workflow**:
  - `make format && git add -A && git commit`
  - Kein pre-commit Hook — ruff würde Commit fehlschlagen lassen, Agent würde dann --no-verify nutzen (verboten)
- **Tests**: `pytest` mit `asyncio_mode=auto`, `httpx.AsyncClient` für API-Tests
- **Linting**: `ruff` für Formatierung und Linting, `mypy` für Typprüfung

## Agent-Branch-Workflow

- Komplexe Multi-file Tasks: `feature/agent-<taskname>`
- Kein direkter Push auf `main` oder `dev`
- Merge nur nach manuellem Review
- Einfache Docs/Fixes: Direkt auf `dev`, dann PR

## Domänen- & Feature-Übersicht (für KIs)

Dieses Repository dokumentiert und verwaltet die Hardware- und Strominfrastruktur (ServerFlow-Konzept). Hier sind die Kernbereiche:

### 1. USV N+1 Dimensionierung & 3-Phasen-Lastberechnung
- **Zweck**: Berechnung der minimalen Anzahl an USV-Modulen und Batteriemodulen, die für eine Autonomiezeit bei Phasenungleichgewicht erforderlich sind.
- **Berechnungslogik**: `app/services/usv_calc.py`
- **Endpunkte**: `/api/v1/usv/simulate` und `/api/v1/usv/status`
- **Modelle**: `Rack` (mit `max_watt` und `usv_n1_redundant`), `Device` (mit Phase L1/L2/L3-Zuweisung und Watt-Nennleistung).

### 2. EPLAN CSV Import & Kabeltyp-Mapping
- **Zweck**: Import von physischen Kabelverbindungslisten, die aus EPLAN exportiert wurden.
- **Parser**: `app/services/eplan_parser.py` (flexibler Parser mit dynamischem Spaltenmapping).
- **Import-Endpunkte**: `/api/v1/import-eplan/preview` (validiert Daten, zeigt Differenzen) und `/api/v1/import-eplan/commit` (persistiert Racks, Devices, Ports und Kabel; mappt freie Typen wie `LWL-LC` auf Enum-Werte wie `LC-LC`).

### 3. Kabellisten-Export
- **Zweck**: Dokumentations-Export für Excel, Calc oder CSV.
- **Exportformate**: CSV, XLSX (via `openpyxl`), ODS (via `odfpy`).
- **Exporter**: `app/services/export_service.py`
- **Endpunkt**: `/api/v1/export/cables`

### 4. Datenbankmodelle (SQLAlchemy 2.0 Async)
- `Rack`: Verwaltet Serverracks (`name`, `standort`, `hoehe_u`, `bemerkung`).
- `Device`: Physische Geräte (`hostname`, `typ` [server, switch, pdu, kentix_raconode, kentix_doormaster, kentix_multisensor, sonstige], `hoehe_u_start`, `u_hoehe`, `side` [left, right, nullable — für 0U PDUs], `phase` [L1, L2, L3], `tdp_watt`, `rack_id`).
- `PduOutlet`: PDU-Steckdosen (`outlet_name`, `phase` [L1, L2, L3], `steckdosentyp` [C13, C19, C14, C20, Schuko, CEE-16A], `max_watt`, `schaltbar`, `connected_device_id`, `connected_port`).
- `DevicePort`: Ports an Geräten (`port_name`, `typ` [RJ45, LC, SC, sonstige], `kabel_id`, `device_id`).
- `Cable`: Physische Kabelverbindungen (`kabel_nr`, `typ` [Cat6, Cat6A, Cat7, DAC, LC-LC, SC-SC, SFP+, Strom-C13, Strom-C19, Strom-Schuko, Strom-CEE-16A-3P, Strom-CEE-32A-3P, Strom-CEE-63A-3P, sonstige], `laenge_m`, `farbe`, `von_device_id`, `von_port`, `nach_device_id`, `nach_port`).

### 5. PDU-Regeln & Validierung
- **1 PDU pro Seite pro Rack**: Pro 0U-Seite (left/right) maximal eine vertikale PDU. Backend: `_check_side_conflict()` in `devices.py` + `pdus.py`. Frontend: Side-Buttons deaktiviert wenn belegt (`occupiedSides`).
- **min_rack_hoehe Filter**: `filteredHW` im Frontend filtert PDUs mit `min_rack_hoehe > rack.hoehe_u` aus. Backend validiert in `_check_rack_height_compatibility()`. 42HE-Rack → nur PDUs mit `min_rack_hoehe <= 42` (keine 47HE-PDUs).
- **0U-PDU füllt Rack-Höhe**: Die 0U-Spalte im Rack-Diagramm wird immer in voller `rack.hoehe_u` Höhe gezeichnet, unabhängig von der physischen PDU-Höhe. `flex-1` auf PDU-Button, `overflow-y-auto` entfernt.

### 6. Port-Konfiguration & Standard-Ports
- **FastAPI Backend**: Standardmäßig auf Port `8003` (`make dev`).
- **SvelteKit Frontend**: Standardmäßig auf Port `5175`. CORS im Backend ist konfiguriert, um Zugriffe von `http://localhost:5175` zu erlauben.

## Makefile-Targets

| Target | Funktion |
|---|---|
| `make dev` | Backend starten (Port 8003) — aktiviert .venv automatisch |
| `make dev-frontend` | Frontend starten (Port 5175) |
| `make dev-all` | Backend + Frontend parallel — für KAiOSS cmd-runner |
| `make help` | Übersicht aller Targets |
| `make test` | pytest |
| `make format` | ruff fix + format |
| `make lint` | ruff + mypy |
| `make migrate-create message='...'` | Alembic Revision |
| `make migrate-apply` | Alembic upgrade head |
| `make clean` | pycache, pyc, .bak bereinigen |

`.project.toml` → `cmd_start = "make dev-all"` (startet Backend + Frontend zusammen)

## Feature-Roadmap

### Phase 1 — Datenmodell bereinigen (PRIORITÄT)
- [ ] `ServerInterface` + `DevicePort` zu einem einheitlichen `Interface`-Modell zusammenführen
- [ ] Tote Modelle entfernen: `KentixReading`, `UsvCalculation`, `DistributionPanel`, `DistributionCircuit`
- [ ] Tote Device-Felder entfernen: `api_url`, `api_key`, `circuit_id`
- [ ] Alembic-Migration für DROP TABLE + Column

### Phase 2 — Export-Vollständigkeit
Bestehend: `/export/cables` (CSV, XLSX, ODS) — ExportService bereits vollständig implementiert.

Fehlend:
- [ ] `GET /api/v1/export/racks` — Rack-Inventar (Rack → Gerät, U-Position, Hersteller, Modell, SN, TDP)
- [ ] `GET /api/v1/export/interfaces` — Geräte-Interfaces (Gerät → Port → Verbunden mit → Zielgerät)
- [ ] `GET /api/v1/export/pdus` — PDU-Belegung (PDU → Steckdose → Phase → Gerät)
- [ ] `GET /api/v1/export/full` — Multi-Sheet XLSX (alle Sheets in einer Datei via openpyxl)

### Phase 3 — Visualisierung
- [ ] Rack-Diagramm: U-Positions-Ansicht, Geräte als farbige Blöcke (1U/2U/4U Höhe)
- [ ] Topologie-Graph: Geräte als Knoten, Kabel als Kanten (D3.js oder Cytoscape.js), rack-übergreifend
- [ ] Interface-Matrix: Tabelle Gerät × Port mit Status (frei/belegt/defekt) und Zielgerät
- [ ] Kabelverfolgung (Trace): Interface A → kompletter Pfad bis Ziel B inkl. Patchpanel

### Phase 4 — Erweiterte Dokumentation
- [ ] PDF-Export: Rack-Diagramm + Kabelliste + Interface-Beschreibung (druckbar)
- [ ] Patch-Panel Support: Zwischenstation im Kabelweg (Switch → Patch → Server)
- [ ] Volltext-Suche: "Welches Gerät hängt an Switch-01 Port 24?"
- [ ] Asset-Export: XLSX mit Geräten, Seriennummern, Positionen (für Asset-Management)

### Phase 5 — Daten & Integration
- [ ] Seed-Script: Die hartcodierten USV-Vorlagen (Wöhrle 40kW, Eaton 93PM etc.) aus dem N+1 Simulator als echte `usv_units`-Einträge in die DB überführen, damit sie im E-Plan-Dropdown global wählbar sind.

## Bekannte Bugs

| Bug | Ursache | Status |
|---|---|---|
| Internal Server Error auf /hardware | `hardware_types.json` kann nicht angelegt werden wenn Disk voll | KNOWN |
| SAWarning: `update_default` in serverflow.py:113 | Ungültiges SQLAlchemy-Argument auf `DistributionCircuit.max_watt` | KNOWN — fällt weg bei Phase-1-Cleanup |
| USV-Kalkulation rechnet alle Rack-Geräte der USV zu | Filterung erfolgt nur per `rack_id`, nicht per Stromkreis-Verknüpfung | KNOWN — Fix: Join über `distribution_circuits → panels → usv_unit_id` |
| Fehlender Unique-Constraint auf `cables.kabel_nr` im ORM | `UNIQUE KEY` im Schema vorhanden, ORM-Model hat kein `unique=True` | KNOWN |

## Verfügbare Claude-Skills

### Öffentliche Skills (`/mnt/skills/public/`)
- `docx` – Word-Dokumente erstellen/bearbeiten
- `pdf` – PDF-Operationen
- `pptx` – PowerPoint-Präsentationen
- `xlsx` – Spreadsheets
- `product-self-knowledge` – Anthropic-Produktinfos
- `frontend-design` – Web-UIs & Komponenten
- `file-reading` – Datei-Inhalte lesen
- `pdf-reading` – PDFs lesen/extrahieren
- `canvas-design` – Visuelles Design / Poster
- `mcp-builder` – MCP-Server erstellen
- `skill-creator` – Skills erstellen/optimieren

### User-Skills (`/mnt/skills/user/`)
- `setup-quality` – Reproduzierbares Projekt-Setup
- `agent-md-deploy` – AGENT.md ins Projekt deployen
- `bash-deploy` – Code als Bash-Heredoc formatieren
- `kaioss-context-sync` – Kontext-Sync via AGENT.md & Cognee
- `kaitix-agent-deploy` – AGENT.md speziell für KAiTix deployen