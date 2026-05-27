# AGENT.md — KAiTix

## ⚠️ WICHTIGSTE REGEL — Gilt für alle KI-Agenten

KAiTix ist ein reines Dokumentations- und Berechnungs-Tool.

VERBOTEN:
- Kein Live-Monitoring
- Keine Echtzeit-Daten
- Keine WebSockets / Polling-Loops
- Keine externen API-Calls zur Laufzeit
- Keine PDU/Kentix API-Calls
- Keine automatischen Aktionen
- Kein automatisches Schalten von Hardware

ERLAUBT — Berechnungen aus DB-Daten:
- USV-Auslegung: Berechnung aus dokumentierten TDP-Werten
- Phasen-Simulation: L1/L2/L3 Lastverteilung berechnen
- USV N+1 Kaltstart-Simulation: mathematisch aus Modulen
- Rack-Belegung: HE-Berechnung aus dokumentierten Geräten
- Kabellisten, Topologie: aus DB lesen/anzeigen
- PDU-Outlet als Info-Text (aus DB, kein API-Call)
- Ausführungs-Status manuell durch Techniker setzen
- Runbook-Checkliste: manuell abhaken

FAUSTREGEL:
Kommt der Wert aus der MySQL-DB → erlaubt.
Kommt der Wert von einem externen Gerät zur Laufzeit → verboten.

Jede neue Funktion die Live-Daten, Polling oder externe API-Calls einbaut ist ein Bug — sofort entfernen.

---

Letzte Aktualisierung: 2026-05-26

---

## Design-Prinzipien (für KI-Agenten: nicht verhandelbar)

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

---

## Projekt-Übersicht

KAiTix — Serverraum-Verwaltung & Runbook Orchestrator.
Dokumentiert Racks, Geräte, PDUs, USV, Kentix-Sensoren,
virtuelle Maschinen und Shutdown/Startup-Runbooks.

**Status:** Aktiv in Entwicklung
**Pfad:** ~/Projekte/aktiv/KAiTix

---

## Stack

- **Backend:** FastAPI + SQLAlchemy 2.x async + aiomysql
- **Frontend:** Svelte 5 — kein TypeScript, plain JavaScript
- **DB:** MySQL 8+ (nur MySQL — kein PostgreSQL, kein SQLite)
- **Migrations:** Alembic (immer via `python3 -m alembic`)
- **Tests:** pytest
- **Linting:** ruff + mypy
- **Port:** Backend 8003

---

## Dev-Umgebung

- **Nix Shell:** `shell.nix` importiert `~/Projekte/nix/common.nix`
- **direnv:** aktiviert nix-shell automatisch beim `cd`
- **venv:** manuell `source .venv/bin/activate`
- **Start:** `make dev-all` → Backend (8003) + Frontend parallel
- **Python:** 3.14 (via nix-shell)
- **Node:** v22.22.2 (nodejs_22)

---

## Architektur-Entscheidungen

### Geräte
- Kentix SmartPDU: `u_hoehe=0`, min_rack_hoehe=42(40HE)/47(47HE)
- Kentix SmartPDU: intelligent, MID-geeicht, schaltbar, RCM, PoE
- Eine PDU pro Rack
- `tdp_watt` ist Fallback — echte Last aus `pdu_outlet_readings`
- Phasen L1/L2/L3: aktuell 12-17 kW unausgeglichen (bekannt, offen)
- Racks: Rittal VX IT / TS IT

### VMs
- Eigene Tabelle `virtual_machines` — NICHT in `devices`
- Kein Proxmox — hypervisor_typ: vmware, hyper-v, kvm, xcpng, sonstige
- `depends_on_vm_id` FK self für Abhängigkeitsgraph

### Power-Domain (Strom & USV)
- **Konzept**: Phasenversorgung (B→C→A) und strikte Überwachung von Leistungsgrenzen.
- **SPOF-Antithesen**: Single-Point-of-Failure Vermeidung ist essenziell. 
  - VDE-Audit Validierungsregeln im Generator-Skript setzen hart `N1_IMPOSSIBLE` (Kein N+1 bei <2 Modulen), `BATTERY_SPOF` (bei <2 Strings) und `EPO_MISSING` (Fehlender Not-Aus, VDE-Verstoß) auf ERROR. Fehlender Maintenance-Bypass (`MBS_MISSING`) erzeugt eine WARNING.
- **Redundancy Path**: Nutzung des Feldes `redundancy_path` (A/B) als explizite Weichenstellung zur Sicherstellung der Tier-III Kompatibilität (Dual-Path Versorgung bis zum Endgerät).
- **Phase Optimizer Sprint**: `phase_optimizer.py` als Wrapper über `PhaseBalancer`
- **Neue Endpoints**: `POST /api/v1/power/phase/optimize/{rack_id}` und `/apply`
- **Frontend**: Imbalance-Badge, Optimizer-Button, Dropdown-Warn-Icon

### Runbooks
- Flexible Ebenen (`runbook_layers`) — nicht hardcodiert
- Startup auto-generierbar aus Shutdown (umgekehrte Reihenfolge)
- Notizen auf 3 Ebenen: pro Layer, pro Gerät, pro Ausführungsschritt
- Ausführungs-Protokoll: `runbook_executions` + `runbook_execution_steps`

### Authentifizierung
- Bewusst KEIN Auth-System — Intranet-only
- Mitarbeitername wird im Frontend einfach eingetippt
- X-Username Header = Freitext, keine Verifikation — so gewollt
- Kein SSO, kein JWT, kein OAuth — nicht implementieren
- Default DB-Credentials admin/root sind für Doku-Tool akzeptabel

### Netzwerk & Middleware
- Kein Rate-Limiting — Intranet-only, kein öffentliches API
- Keine IP-Logging Middleware
- Keine externen Netzwerk-Calls aus dem Backend
- KAiTix kommuniziert nur mit den lokalen DBs

---

## Implementierte Features (diese Session)

### ✅ KAiTix Sprint 2 — Power Protokoll + Modal Refactoring
- **Backend API:** Neuer Endpoint `GET /api/v1/power/audit/{usv_unit_id}` zur On-The-Fly VDE-Compliance Prüfung anhand von `app/domains/power/services/usv_calc.py -> audit_vde_compliance()`.
- **Frontend Refactoring:** Die Geräte-Detail-Ansicht in `racks/+page.svelte` wurde in ein zentriertes Modal (Overlay) mit drei Tabs (Geräte-Details, Ports & Kabel, VDE Protokoll) umgebaut.
- Das VDE Protokoll-Tab visualisiert den Audit-Status sowie die Last-Historie asynchron.

### ✅ Landingpage /landingpage
- Eigenständige Route `/landingpage` ohne App-Layout (keine Sidebar, kein Header)
- Haupt-App-Chrome und Routen in Route-Group `(app)/` isoliert, um das Root-Layout für `/landingpage` auszuschließen.
- Hero-Section mit Hintergrundbild `/assets/hero-serverraum.jpg` (mit `filter: brightness(0.45) contrast(1.05) saturate(1.2)`)
- Live-Stats via fetch: `/api/v1/racks`, `/api/v1/devices`, `/api/v1/dashboard/stats`
- Health-Badge via `/api/v1/health` (grün/rot)
- Lightbox: Klick auf Hero-Bild oder Kamera-Icon öffnet Vollbild, ESC oder Klick außen schließt
- Feature-Grid 6 Module + Stack-Bar
- Foto gesichert unter `docs/screenshots/hero-serverraum.jpg`

### ✅ Backend Landingpage-Endpoints
- GET `/api/v1/health` → `{"status": "healthy", "message": "System online"}`
- GET `/api/v1/dashboard/stats` → `{"total_power_kw": float}` (Summe aller tdp_watt aus devices-Tabelle, geteilt durch 1000)
- Router: `app/domains/hardware/routers/dashboard.py`

### ✅ Dashboard-Routing-Anpassungen
- Root `/` zeigt weiterhin das Dashboard (unter `(app)/+page.svelte` und `(app)/+layout.svelte`)
- KAiTix-Logo in Sidebar verlinkt auf `/landingpage`

### ✅ Bugfix check_execution_step
- `id == sid` → `runbook_device_id == sid` korrigiert

### ✅ Uncheck Endpoint
- `DELETE /api/v1/executions/{eid}/steps/{sid}/uncheck`

### ✅ X-Username Audit-Logging
- Header `X-Username` → `erstellt_von`, `gestartet_von`, `abgehakt_von`

### ✅ Execution Frontend
- Checkboxen check/uncheck
- Wer/wann neben Haken angezeigt
- Startup: umgekehrte Layer-Reihenfolge

### ✅ Runbook Planer (Drag & Drop)
- 2-Spalten-Layout: Layer links, Sidebar rechts
- Sidebar: VMs (rosa) + Geräte (blau) + Suchfilter
- HTML5 Drag & Drop: Ressource → Layer, Gerät → anderer Layer
- Freitext-Geräte per D&D

### ✅ VM-Abhängigkeitsgraph
- Tab-Umschalter: Tabelle / Abhängigkeitsgraph
- Level-Berechnung (cycle-resistent)
- SVG Bezier-Kurven mit Richtungspfeilen
- Hover: Vorgänger grün, Nachfolger rosa, Rest abgedunkelt

---

## Test-Status
 
- pytest: 24 Tests grün ✅
- npm run build: grün ✅
 
---
 
## Offene TODOs
 
- [x] Phasen-Imbalance beheben (12-17 kW unausgeglichen, L1/L2/L3)
- [ ] Protokoll-Tab: historische Ausführungen anzeigen
- [x] PDF-Export Runbook (Client-seitig via window.print)
- [x] Markdown-Export Runbook (Client-seitig serialisiert)
- [ ] Management-URL / Deep-Link (statischer Link) pro Gerät im Runbook (KEIN Live-Polling!)
 
---
 
## Bekannte Bugs / Issues
 
- Phasen-Imbalance ~12-17 kW (dokumentiert, noch nicht behoben)
 
---
 
## Verbotene Änderungen
 
- ❌ TypeScript einführen (Svelte 5 plain JS)
- ❌ PostgreSQL oder SQLite (nur MySQL)
- ❌ VMs in `devices` eintragen
- ❌ Proxmox als hypervisor_typ
- ❌ Neue pip-Pakete ohne Rückfrage
- ❌ Bestehende Router-Struktur brechen
- ❌ Landingpage-Route in App-Layout einbetten (muss sidebar-frei bleiben)
 
---
 
## Konventionen
 
- Alembic immer: `python3 -m alembic upgrade head`
- Router-Struktur: `app/domains/<domain>/router.py`
- Schemas: `app/schemas/<domain>.py`
- Keine globalen pip installs (immer venv)
- Seed-Scripts: Bestehende Seed-Scripts in `scripts/` (z.B. `seed_testdata.py`) immer komplett überschreiben (Clean Slate mit `drop_all`) oder sinnvoll ergänzen. Keine neuen, redundanten Seed-Skripte anlegen.
- **Zero-U PDUs:** PDUs, die vertikal an der Seite im Rack montiert werden (Zero-U), MÜSSEN die Attribute `side="left"` oder `side="right"` sowie `u_position=0` besitzen. Zudem sollten korrekte Kentix-Modellbezeichnungen für vertikale PDUs (z.B. `SmartPDU Vertikal 40HE 3P-32A`) verwendet werden.
---
 
## Referenzen
 
- Gemini-Prompt Runbook Orchestrator: `gemini_prompt_runbook_orchestrator.md`
- Globale Umgebung: `~/Projekte/AGENT.md`
- nixubuntu Repo: github.com/diebugger-tech/nixubuntu
 
---
 
**Letzte Session**
**Datum:** 2026-05-27
**Was gemacht (Runbook Print & Export Sprint):**
- Client-seitiger Print-Layout-Support für A4 Portrait ([RunbookPrint.svelte](file:///home/andreas/Projekte/aktiv/KAiTix/frontend/src/lib/components/RunbookPrint.svelte)) mit globalen Print-Media-CSS-Regeln in [layout.css](file:///home/andreas/Projekte/aktiv/KAiTix/frontend/src/routes/layout.css).
- Client-seitige Markdown-Generierung und lokaler Datei-Download in [+page.svelte](file:///home/andreas/Projekte/aktiv/KAiTix/frontend/src/routes/(app)/runbook-orchestrator/[id]/+page.svelte).
- Ersetzung des PDF-Buttons durch einen "Drucken"-Button mit Printer-Icon.
- Validierung, dass `npm run build` und `pytest` weiterhin erfolgreich durchlaufen.

**Nächste Schritte:**
- Phasen-Imbalance beheben (12-17 kW unausgeglichen)
- Healthcheck-URL pro Gerät im Runbook integrieren
- Protokoll-Tab: historische Ausführungen anzeigen
