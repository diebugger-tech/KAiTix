# Changelog

Alle wesentlichen Änderungen am Projekt werden in dieser Datei dokumentiert.

## [Unreleased]

### Hinzugefügt
- **Desktop-App (Linux, Prototyp):** `sh desktop/install.sh` legt Starter und Menüeintrag an;
  KAiTix läuft als eigenes Fenster auf 127.0.0.1 mit Daten in `~/.local/share/kaitix`.
  „Nach Updates suchen“ holt neue Commits per git und baut neu, mit Sicherung der
  Datenbank vor Migrationen. Beschreibung: `desktop/README.md`.
- **Serverraum-Umbau** (`/umbau`): Kabel je Gerät erfassen, Soll-Stand einfrieren, jedes
  Stecker-Ende abklemmen und nach dem Umbau am Soll-Port wieder anklemmen; Abweichung nur mit
  Grund, Protokoll je Buchung. Beschreibung in `docs/umbau.md`. Migration `a6f7bab2f1b2`.
- **Kabeltyp-Katalog** (`/kabeltypen`): Kabeltypen mit Kategorie, Steckern und Enden je Seite;
  Kabel verweisen über `kabeltyp_id` darauf. Migration `52e1b97080a3`.
- **Breakout-Kabel:** Jeder Strang hat eigenes Ziel-Gerät und eigenen Port. Migration `27f768e65156`.
- **Umbau: Kabel nachtragen.** Ein im Rückbau gefundenes Kabel, das nicht in der Kabelliste
  steht, wird mit Typ und Enden im Umbau aufgenommen und muss abgeklemmt werden; die
  Kabelliste bleibt unberührt. Entfernen möglich, solange nichts abgeklemmt ist.
- **Umbau: Druckliste.** Alle Enden nach Rack und Gerät mit Position, Soll-Port, Gegenseite,
  Länge und Abhakfeldern; nach dem Abschluss mit Ist-Port und Grund.
- **Umbau: Soll mit Position und Länge.** Das Einfrieren kopiert HE-Position des Geräts und
  Kabellänge. Migration `d4ed62bc8ae1` (auch für den Nachtrag).
- **Ports überschreibbar:** `make dev-all BACKEND_PORT=… FRONTEND_PORT=…` für eine zweite Instanz.
- README: Abschnitt „Update einer bestehenden Installation".
- Runbook Orchestrator: PDF Print-Laufzettel mit Rack Elevations und Zero-U Highlighting
- CSV Import: Aggregierte Fehlerdarstellung (Zusammenfassung fehlerhafter Zeilen)
- **Container-Setup (3-Befehl-Onboarding):** `podman/docker compose up --build` bringt das
  Projekt auf einem frischen Rechner vollständig zum Laufen (nur Container-Engine als Voraussetzung).
- **`scripts/db_init.py`:** Schema-Bootstrap für leere DBs (`create_all` + `alembic stamp head`),
  da keine Initial-Create-Migration existiert — `alembic upgrade head` allein scheiterte auf leerer DB.
- **Auto-Seeding:** Demo-Daten werden beim ersten Start automatisch geladen (nur wenn DB leer,
  via `seed_testdata.py --if-empty`); abschaltbar über `SEED_DEMO_DATA=false`.
- **Compose Watch:** `podman compose watch` baut bei Quelländerungen automatisch neu (`develop.watch`).

### Geändert
- CSV Import: "Importieren"-Button wird strikt gesperrt, sobald Fehler in der Preview-Tabelle existieren
- CSV Import: Backend-Validierung um echte Rack-HE-Overlap-Logik erweitert
- compose: DB-Host fest auf Service `db` (nicht mehr aus `${DATABASE_URL}` — eine lokale Dev-`.env`
  kann den Container nicht mehr brechen); Healthcheck via `127.0.0.1`/`-uroot`; `service_healthy`-Gate.

### Behoben
- Umbau: Kabel ohne Kabelnummer sperren das Einfrieren; ohne Nummer war ein Kabel nach dem
  Abklemmen beider Enden nicht mehr zuzuordnen.
- Umbau: Anklemmen mit anderer Groß-/Kleinschreibung des Soll-Ports („ETH0“) gilt nicht mehr
  als Abweichung.
- Druck: Seitenleiste und Kopfzeile der App wurden mitgedruckt (`.flex` schlug die
  Ausblende-Regel).
- CSV- und EPLAN-Import setzen den Kabeltyp aus dem Katalog; importierte Kabel sperren
  das Einfrieren eines Umbaus nicht mehr pauschal.
- Frontend: Abgelehnte Anfragen (4xx, z. B. 409 Port belegt) schalten den Backend-Status
  nicht mehr auf offline und landen nicht mehr in der Konsole; 422-Validierungsfehler
  zeigen Feld und Meldung statt „[object Object]“.
- Kabel: Ports im Schreibweg, Belegungsprüfung und Kabelnummern-Generator.
- Frontend-Build brach ab: `{@const}` in `(app)/+layout.svelte` war kein direktes Kind des `{#each}`.

### Entfernt
- VDE Protokoll-Reiter im Rack-Detailmodal (wird in die eigene `/usv`-Route verschoben)

## [1.0.0] — 2026-05-22

### Hinzugefügt
- Rittal VX IT / TS IT Racks im Hardware-Katalog (8 Varianten, 42/47 HE, 600/800mm)
- Kentix SmartPDU Modelle (Zero-U vertikal, min_rack_hoehe Validierung)
- RackModal als wiederverwendbare Svelte-Komponente (Dashboard + Racks)
- Rack-Modell Auswahl mit automatischer Höhen- und Breitenvorgabe
- PDU-Seiten-Zuordnung (0UL / 0UR, max. 1 PDU pro Seite)
- Topologie-Filter (Geräte, Kabel, Ansicht, Rack-Filter)
- Bearbeiter-Freitext im Frontend (localStorage, X-Username Header)
- CORS auf localhost beschränkt
- Hardware-Katalog kategorie-spezifische Kartenansicht

### Geändert
- hoehe_u Eingabe: Dropdown statt Freitext (dynamisch aus Katalog)
- breite_mm: aus Rack-Modell übernommen, nicht mehr manuell
- USV-Berechnung: Fallback-Kette (Kentix-Messung → psu_nennwatt → tdp_watt)

### Behoben
- Schema-Drift breite_mm (fehlte im ORM/Pydantic)
- alarm_ok Logik invertiert in kentix.py
- min_rack_hoehe: 40HE-PDUs korrigiert auf 42 (nicht 40)

## [0.1.0] — 2025

### Hinzugefügt
- Initiales FastAPI Backend + Svelte 5 Frontend
- Rack-, Geräte-, Kabel- und USV-Verwaltung
- Kentix SmartPDU Integration (REST-API)
- Export: Excel, ODS, CSV, PDF
- Hardware-Katalog mit JSON-Datei
- Topologie-Visualisierung
