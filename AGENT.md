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

Letzte Aktualisierung: 2026-05-25

---

## Projekt-Übersicht

KAiTix — Serverraum-Verwaltung & Runbook Orchestrator.
Dokumentiert Racks, Geräte, PDUs, USV, Kentix-Sensoren,
virtuelle Maschinen und Shutdown/Startup-Runbooks.

**Status:** Aktiv in Entwicklung
**Pfad:** ~/Projekte/aktiv/KAiTix

---

## Stack

- **Backend:** FastAPI + SQLAlchemy 2.x sync + PyMySQL + aiomysql
- **Frontend:** Svelte 5 — kein TypeScript, plain JavaScript
- **DB:** MySQL 8+ (nur MySQL — kein PostgreSQL, kein SQLite)
- **Migrations:** Alembic (immer via `python3 -m alembic`)
- **Tests:** pytest (20 Tests, alle grün)
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

- pytest: 20 Tests grün ✅
- npm run build: grün ✅

---

## Offene TODOs

- [ ] Phasen-Imbalance beheben (12-17 kW unausgeglichen, L1/L2/L3)
- [ ] Protokoll-Tab: historische Ausführungen anzeigen
- [ ] PDF-Export Runbook
- [ ] Markdown-Export Runbook
- [ ] Healthcheck-URL pro Gerät im Runbook

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

---

## Konventionen

- Alembic immer: `python3 -m alembic upgrade head`
- Router-Struktur: `app/domains/<domain>/router.py`
- Schemas: `app/schemas/<domain>.py`
- Keine globalen pip installs (immer venv)

---

## Referenzen

- Gemini-Prompt Runbook Orchestrator: `gemini_prompt_runbook_orchestrator.md`
- Globale Umgebung: `~/Projekte/AGENT.md`
- nixubuntu Repo: github.com/diebugger-tech/nixubuntu

---

## Letzte Session

**Datum:** 2026-05-25 (Nachmittag)
**Was gemacht:**
- Neue API & DB-Migration für Runbook-Execution `note` Spalte implementiert (erzwingt Pflicht-Begründung beim Verwerfen).
- Backend-Validierung für Status `verworfen` (HTTP 400 ohne Notiz) hinzugefügt und getestet.
- Planer-Sperre & Tab-Trennung im Frontend implementiert: Planer ist komplett schreibgeschützt und Ressourcen-Katalog deaktiviert (pointer-events-none), wenn eine Ausführung offen ist.
- PDU-Outlet Info-Badges in allen drei Ansichten (Planer, Ausführung, Protokoll-Details) eingebunden.
- Layer Inline-Dropdown Ebenen-Hinzufügung per Dropdown-Templates implementiert.
- Automatisierte GUI-Tests (`test_gui.py`) an neuen Workflow angepasst und erfolgreich validiert.

**Nächste Schritte:**
- Phasen-Imbalance beheben (12-17 kW unausgeglichen)
- PDF-Export für Runbook
- Healthcheck-URL pro Gerät im Runbook integrieren
