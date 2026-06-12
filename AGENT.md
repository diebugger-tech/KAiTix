# KAiTix — AGENT.md
*Letztes Update: 2026-06-10*

## Projektübersicht

**KAiTix** ist ein intranet-only, single-user Infrastruktur-Dokumentations- und Runbook-Orchestrierungstool für Rechenzentren.

**Kernphilosophie:** Dokumentation only — kein Monitoring, keine Echtzeit-Daten, keine Automation.
PDUs und Kentix-Geräte werden dokumentiert (welche Steckdose/welches Gerät), nicht gesteuert.
Runbooks sind Techniker-Checklisten, keine Automation-Trigger.

**Ursprung:** ServerFlow (Python CLI, sync SQLAlchemy, PyMySQL) war der Vorgänger.
KAiTix ist die Neuentwicklung (FastAPI, async, Svelte5, Alembic, MySQL8).
ServerFlow-Dateien dienen als Referenz für Domänenwissen (USV-Berechnung, Kentix-Integration).

---

## Stack

| Komponente | Technologie |
|---|---|
| Backend | FastAPI, async SQLAlchemy + aiomysql, Alembic |
| Frontend | Svelte 5 (keine SSR-Props-Spread: `...props` verboten) |
| Datenbank | MySQL 8 (einzige unterstützte DB) |
| Containerisierung | Podman (bevorzugt), Docker (dokumentiert als Alternative) |
| CLI-Agent | Claude Code (Implementierung) |
| Planung/Review | Claude.ai Web-Chat (diese Konversation) |

**Projektpfad:** `~/Projekte/aktiv/KAiTix`
**Verwandtes Projekt:** nixubuntu @ `github.com/diebugger-tech/nixubuntu`
**Branch:** `feature/agent-runbook-print-export`

---

## Ausführungsmodell

- Andreas reviewt Implementierungspläne **bevor** Claude Code ausführt
- Explizite Verifikationsschritte nach jeder Änderung erwartet
- Claude Code committet nach jedem Fix
- Bestehende Funktionalität ist bei Feature-Ergänzungen zwingend zu erhalten
- **DB-Migrationen:** Immer zuerst zeigen, erst nach explizitem "Go" anwenden

---

## Aktueller Stand (2026-06-10)

### Zuletzt abgeschlossen (diese Session)

**Phase 5 — Performance & Backend Härtung (abgeschlossen):**
- **N+1 / Kaltstart Latenz Fix (BUG-01):**
  - Massive Latenz (bis zu 40s) beim ersten Laden des Dashboards behoben.
  - Ursache: Kaskadierende `lazy="selectin"` Queries für `Device.dependencies` und `Device.depended_by` entfernt (jetzt `lazy="raise"`).
  - Explicit `selectinload` in `get_device_options` Router eingebaut.
  - `lifespan` Context-Manager in FastAPI integriert, um den MySQL-Connection-Pool beim Start aufzuwärmen (`SELECT 1`).
- **Testdaten & IPv6:**
  - `seed_testdata.py` erweitert: IPv6-Adressen für Compute-Server eingefügt und DB erfolgreich geseeded, um Showcase-Vollständigkeit (inkl. Referenz IPv6-Daten) herzustellen.

**Phase 4 — UX & UI Refactoring (abgeschlossen):**
- **Dark Mode Komplett-Redesign:** Ablösung des altbackenen Grau-Grün-Themes durch ein hochkontrastiges, modernes "Slate & Emerald" Farbschema in Svelte 5.
  - Satter `slate-950` Basis-Hintergrund für starke Tiefe, `slate-900` für Cards.
  - Gestochen scharfe Textfarben (`slate-50`, `slate-300`, `slate-400`) zur Behebung gravierender Lesbarkeitsprobleme bei kleinen Schriften (z.B. Auslastung, Standorte).
  - Leuchtender `emerald-500` Akzentton für Ladebalken, Ränder und Buttons.
- **Racks-Übersicht & Filter-Sync (RackFilterBar):**
  - Redundante, linke Rack-Liste entfernt, um vollen Fokus auf das Grid und die Topbar-Suche zu legen.
  - 2-Wege-Synchronisation (`$effect`) zwischen Dropdown-Filter und ausgewähltem Rack repariert (verhinderte "Empty Select" durch int/string mismatch).
  - Sauberes Reset-Verhalten auf "Alle" implementiert.

**Phase 3 — Daten-Härtung (Import & Export) abgeschlossen:**
- **Runbook Laufzettel / Print Export:** Sauberes `@media print`-Layout ohne störende App-UI. `RunbookPrint`-Komponente mit Checklisten und dynamisch generierten Rack Elevations für Zielgeräte. Zero-U PDUs und Geräte sind berücksichtigt und visuell markiert.
- **CSV-Import Härtung:**
  - Rack-Overlap-Validierung (echte HE-Intervall-Logik beim Import).
  - Button-Locking via Preview: Import-Button wird gesperrt, sobald Fehler (Kollisionen, unauffindbare Racks etc.) in der Preview-Tabelle existieren.
  - Gruppierte Fehlerdarstellung: Übersichtliche Aggregation der Fehlermeldungen oberhalb der CSV-Tabelle ("3x Rack-Kollision").
- **Bug-Fix Rack-Detail:** `selectedDevice.typ === 'usv'` Check und der "VDE Protokoll"-Reiter wurden aus dem allgemeinen IT-Rack-Detailmodal entfernt, da USVs als Standalone-Einheiten in eigenen Schränken stehen und eigene Ansichten bekommen.

**Dashboard, 3D & USV-Verbesserungen** — komplett implementiert und gepusht:
- 3D-Orbit-Ansicht der Topologie (three.js, ADDITIV neben 2D-SVG; eigene Komponente Topology3D.svelte; MeshStandardMaterial + Licht; EdgesGeometry-Rackrahmen; CSS2DRenderer-Labels mit pointerEvents:none; OrbitControls enableDamping + controls.update() im Loop; Raycaster nur gegen deviceMeshes; SSR-Guard via onMount). RackFilterBar wirkt auch in 3D.
- topologyColors.ts: zentrale Farbquelle für Gerätetypen/Phasen, von 2D-SVG UND 3D gemeinsam genutzt (Single Source).
- Dashboard: PDUs seitlich am Mini-Rack (RackFrontView.svelte extrahiert, von Racks-Seite + Dashboard geteilt); gezieltes Klick-Routing (Gerät/PDU -> ?rack=X&device=Y öffnet Panel; Rahmen -> ?rack=X). Racks-Seite versteht jetzt &device-URL-Param.
- USV-Auslegung: Batteriespannung pro USV-Vorlage (Hochvolt) statt 48V-Default; Entladestrom rechnet gegen Entladeschluss (Faktor 0,85) für Kabel-/Sicherungsdimensionierung; Dimensionierungsrechner-Last aus Simulator-Gesamtlast (L1+L2+L3) vorbelegt + editierbar mit Abweichungshinweis; Batterietyp auf EIN Dropdown zusammengeführt (Single Source batType), "Blei-Säure (offen)" entfernt. Optionen: VRLA, LFP, Li-Ion NMC/NCA.
  OFFEN/TODO: Wöhrle-LFP-Strangspannung ist Platzhalter (400V), vor echtem Beschaffungs-Export aus Datenblatt bestätigen.

**E-Plan Batterie-Strang-Erweiterung** — komplett implementiert und gepusht:
- Alembic-Migration `359168ea3c12`: `battery_strings`, `blocks_per_string`, `block_voltage_v`, `block_capacity_ah` zu `usv_units` (mit `server_default`)
- E-Plan Blatt 1: BAT-Dummy ersetzt durch `-X-BAT` DC-Abgang + `-W3 NYY-J 2×25mm²` mit Verweis auf Blatt 3
- E-Plan Blatt 3: dynamischer Batterie-Strang-Stromlaufplan (schematisch, aus DB generiert)
  - 2 Stränge (=BAT-A, =BAT-B), je 4 schematische Blöcke + gestrichelte Linie + "Blk N"
  - NH-Trennleiter `-F-BAT-A/B`, BMS-Marker (gelbes "M") an Block 2
  - DC-Sammelschiene mit berechneter Spannung + Gesamtkapazität
- USV Batterieschrank-Tab: neue Zeile "Strang-Redundanz (Strangausfall N-1)"
  - Nutzt bestehende `FaultSimulationEngine.calculate_battery_runtime_peukert()`
  - Korrekte Formel: verbleibende Stränge (`battery_strings - 1`) tragen volle Last
  - Ampel: ≥10 min grün, 5–10 min gelb, <5 min rot
- `requirements.txt`: `fastapi[standard]>=0.110.0` + `cryptography>=42.0.0` ergänzt

### Früher abgeschlossen

- IPAM-Modul (VLAN/Subnet-Modelle, IP-Kollisionserkennung, GET-only Routes, Seed-Daten)
- Kaskadierende Rack-Filter (Standort → Rackreihe → Rack) als `RackFilterBar.svelte`
- Root-Cause-Fix: `rackreihe` fehlte im Topology-API-Serializer
- Runbook Orchestrator: komplett (Drag & Drop, Execution, VM-Graph, 20 Tests grün)
- Code-Audit: 31 Findings, Sprint-1-Priorities identifiziert
- E-Plan Blatt 3 (initiale Version): 2-strängige Batterieanlage + BMS im CAD-E-Plan-Stil
- Tests: 24/24 grün (pytest.ini mit `asyncio_mode = auto`, conftest.py repariert)
- Ruff: 0 Fehler

---

## Offene Punkte (priorisiert)

### 🟡 Sprint 2 (Nächste Schritte: Power Audit Refactoring)

Das Ziel für den kommenden Schritt ist es, die USV-Prüfung und Dimensionierung aus den alten Script-Dateien in echte Backend-Services zu überführen und im USV-Bereich des Frontends sichtbar zu machen.

- **Refactoring Service:** `audit_vde_compliance()` aus `scripts/power_setup_generator.py` in einen dedizierten FastAPI Service (z.B. `app/domains/power/services.py`) extrahieren.
- **Backend API:** Neuer Endpoint `GET /api/v1/power/audit/{usv_unit_id}`.
- **Pydantic Schemas:** `UsvCalculationResponse`, `VdeAuditResult`, `PowerAuditResponse` für saubere Typisierung anlegen.
- **Frontend UI (`/usv`):** Ein "Protokoll"-Tab oder eine Detailansicht für die USV-Einheit bauen, wo historische `usv_calculations` und das Live-VDE-Audit (Compliance) übersichtlich visualisiert werden.

### 🟢 Backlog / Optional (Neue Ideen)

- 3D-Orbit-Legende (Packet-Tracer-artig): erklärt 3D-spezifische Elemente (Rackreihen=Tiefe, Standorte=getrennte Blöcke, PDUs=seitliche Zero-U-Bars, Kabelfarben).
- Blast-Radius-Hover: Hover auf PDU/Switch hebt angeschlossene Geräte hervor, Rest dimmt (Ausfallsimulation visuell).
- Kabel-Tracing in der Rack-Frontansicht (SVG-Linien Gerät->Switch).
- PDU-Kollisionscheck: physische PDU-Längen (mm/U) gegen Rackhöhe prüfen (analog zur bestehenden min_rack_hoehe-Validierung; braucht neues Feld im Hardware-Katalog).
- Print-Ready Rack Elevations: s/w-optimiertes Vektor-PDF der Frontansicht + PDU-Belegungstabelle (= deckt sich mit Roadmap-Punkt PDF/Markdown-Export).
- Natrium-Ionen-Batterietyp: aufnehmen, sobald Wöhrle/Eaton ein beschaffbares Produkt mit Datenblatt-Werten (Spannung, Peukert, Entladeschluss) liefern — derzeit nur Prototypen, keine validen Auslegungsparameter.
- USV-Bereich-Audit: systematische Prüfung auf weitere "zwei Wahrheiten" / falsche Bezugsgrößen (in dieser Session 4 Einzelfälle gefunden).

### 🟢 Backlog / Optional (Alt)

- USV-Dropdown im E-Plan (Schritt 5 der Batterie-Erweiterung)
- Testdaten Seed-Script
- ~PDF/Markdown Export~ (In Print-Funktion von Runbook umgesetzt)
- Phasen-Imbalance L1/L2/L3 Dokumentation
- 26 verbleibende TypeScript-Fehler (kein Laufzeit-Impact)
- E-Plan / Einlinienschaltbild Generator als SVG (langfristig)

### Sprint 1 Bug-Backlog (aus Audit)

- CSV-Import silent data loss (rollback in loop)
- EPLAN variable scope bug
- `api.ts:441` falsche URL (`/ports` → `/interfaces`)
- Fehlendes `Rack.max_watt` ORM-Feld
- BUG-01 (blocking I/O) — deprioritiert (single-user context)

---

## Key Learnings & Prinzipien

- **Single-user Scope ändert Risikokalkulation:** BUG-01 (blocking I/O) akzeptabel
- **Serializer-Vollständigkeit ist kritisch:** `rackreihe`-Bug als Referenzfall
- **Seed-Scripts müssen auf async DB-Connection targeten**
- **Conditional Rendering muss konsistent mit refaktoriertem State bleiben**
- **AGENT.md muss async Stack korrekt dokumentieren** (kein sync/PyMySQL)
- **server_default bei NOT NULL Spalten zwingend** wenn Tabelle bereits Zeilen hat
- **Single Source statt zweitem State:** Batterietyp (batType/dimType) und Dimensionierungs-Last (dimLoad) waren je doppelt mit isoliertem State und liefen still auseinander -> ein Verbraucher liest den zentralen Wert, kein zweiter State. Pattern bei jeder neuen Eingabe prüfen.
- **three.js in Svelte5:** Initialisierung nur clientseitig (onMount), sauberes Cleanup in onDestroy (dispose, Frame canceln, Listener entfernen), sonst SSR-Crash / WebGL-Leak.
- **Beschaffungstool-Defaults:** müssen zur gewählten Vorlage passen; falsche hartkodierte Defaults (48V) erzeugen plausible aber falsche Zahlen — in einem Dimensionierungstool gefährlicher als gar kein Default.
- **Svelte 5:** kein `...props` spread in Layout-Komponenten (SSR-Bug)
- **Batterie-Strang-Formel:** Bei N-1 tragen verbleibende Stränge die **volle** Last (nicht geteilt)
- **E-Plan schematisch:** 4 Blöcke + gestrichelte Linie ist professioneller als 32 winzige Blöcke

---

## Verfügbare Claude-Skills

| Skill | Zweck |
|---|---|
| `setup-quality` | Reproduzierbares Projekt-Setup |
| `kaioss-context-sync` | Kontext-Sync via AGENT.md |
| `kaitix-agent-deploy` | AGENT.md ins KAiTix-Projekt deployen |
| `bash-deploy` | Code als Bash-Heredoc formatieren |
| `agent-md-deploy` | Generisches AGENT.md-Deploy |
| `sprint-closing` | Sprint abschließen |
| `kaitix-domain` | KAiTix-Domänenwissen |
| `code-review` | Code-Review |
| `skill-health-check` | Skill-Zustand prüfen |

---

## Technische Referenz

### DB-Migrationen
```bash
# Neue Migration erstellen (zeigen, nicht ausführen!)
alembic revision --autogenerate -m "beschreibung"
# Nach Review anwenden
alembic upgrade head
# Status prüfen
alembic current
```

### Dev-Setup
```bash
nix-shell
make install   # einmalig
make dev-all   # Backend + Frontend starten
```

### Tests
```bash
pytest                    # alle Tests
pytest -x                 # stop on first failure
ruff check app/           # Linting
```

### Git-Workflow
```bash
# Vor jedem Feature: snapshot
git add -A && git commit -m "chore: snapshot vor <feature>"
# Feature committen
git add -A && git commit -m "feat: <beschreibung>"
git push --set-upstream origin <branch>
```
