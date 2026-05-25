# AGENT.md — KAiTix Architektur, Entscheidungen & Backlog

## Projektziel

KAiTix ist eine technische Hardwaredokumentation für Serverräume.
Kernfunktion: lückenlose Quelle-Ziel-Dokumentation jeder physischen
Verbindung (Netzwerk, Glasfaser, Strom) zwischen Geräten — auch
rack-übergreifend.

**Was KAiTix ist:**
- Statische Hardwaredokumentation (Racks, Geräte, Kabel, Interfaces)
- Dokumentation der VM-Landschaft (virtuelle Maschinen mit Host-Server-Zuordnung)
- Runbook Orchestrator: Planung, Ausführung und Protokollierung von Shutdown-/Startup-Sequenzen
- USV-Simulation auf Basis dokumentierter Nennleistungen (offline/mathematisch)
- Statische Validierungen beim Einbauen (z.B. min_rack_hoehe vs. rack.hoehe_u)
- Periodische Datenerfassung von Kentix SmartPDU via REST-API
  (für USV-Berechnung — kein Live-Monitoring, kein Echtzeit-Dashboard)

**Was KAiTix nicht ist:**
- Kein SNMP-Monitoring / kein Echtzeit-Dashboard
- Kein Alarmsystem (Kentix-Alarme werden erfasst, nicht live angezeigt)
- Kein Ersatz für KentixONE
- Keine Live-Daten von VMs — rein dokumentarisch

---

## Stack (fest — nicht ändern)

| Schicht    | Technologie                              |
|------------|------------------------------------------|
| Frontend   | Svelte 5, Vite, kein TypeScript          |
| Backend    | FastAPI + Pydantic v2                    |
| ORM        | SQLAlchemy 2.x **async** + aiomysql (App), PyMySQL (Alembic) |
| DB         | MySQL 8+ — eine einzige DB **`kaitix`**  |
| Config     | python-dotenv — `.env` im Projektroot    |
| Live       | FastAPI SSE (kein SurrealDB, kein WS)    |
| Deployment | Lokal / NixOS / Docker                   |

Kein PostgreSQL. Kein SQLite. Kein SurrealDB. Kein zweites ORM.

> **DB-Name:** Die Datenbank heißt `kaitix` (nicht `serverflow` — alter Name).
> **Credentials lokal:** `kaitix:kaitix@127.0.0.1:3306/kaitix` (in `.env`).
> **`.env` Pflicht:** Ohne `.env` im Projektroot schlägt Backend und Alembic fehl!

---

## Hardware-Ökosystem (Referenz)

### Racks

| Modell                    | Höhe  | Breite | Tiefe  | PDU-Eignung         |
|---------------------------|-------|--------|--------|---------------------|
| Rittal VX IT 42HE 600mm   | 42 HE | 600mm  | 1000mm | SmartPDU 40HE (eng) |
| Rittal VX IT 42HE 800mm   | 42 HE | 800mm  | 1000mm | SmartPDU 40HE ✓     |
| Rittal VX IT 47HE 600mm   | 47 HE | 600mm  | 1000mm | SmartPDU 47HE (eng) |
| Rittal VX IT 47HE 800mm   | 47 HE | 800mm  | 1000mm | SmartPDU 47HE ✓     |
| Rittal TS IT 42HE 600mm   | 42 HE | 600mm  | 1000mm | SmartPDU 40HE (eng) |
| Rittal TS IT 42HE 800mm   | 42 HE | 800mm  | 1000mm | SmartPDU 40HE ✓     |
| Rittal TS IT 47HE 600mm   | 47 HE | 600mm  | 1000mm | SmartPDU 47HE (eng) |
| Rittal TS IT 47HE 800mm   | 47 HE | 800mm  | 1000mm | SmartPDU 47HE ✓     |

- Kentix bietet passgenaue Montagekits + Tür-Adapter für alle Rittal-Modelle
- **800mm empfohlen** für Kentix SmartPDU Zero-U (seitliche Montage)
- **600mm möglich aber eng** — Kentix warnt explizit davor
- **42HE-Rack** → passt SmartPDU 40HE (min_rack_hoehe=42)
- **47HE-Rack** → passt SmartPDU 47HE (min_rack_hoehe=47)
- `breite_mm` wird in DB gespeichert — Validierung ob PDU passt
- Bei 600mm + Zero-U PDU → Warnung im Frontend

### PDUs — Kentix SmartPDU
Vertikale (Zero-U) PDUs werden seitlich montiert, belegen keine HE.

| Modell                       | ID  | u_hoehe | min_rack_hoehe |
|------------------------------|-----|---------|----------------|
| SmartPDU 3P-16A              | 16  | 0       | **42**         |
| SmartPDU 3P-32A              | 17  | 0       | **42**         |
| SmartPDU Dual 3P-32A         | 18  | 0       | **42**         |
| cXale SmartPDU 40HE 3P-16A   | 19  | 0       | **42**         |
| cXale SmartPDU 40HE 3P-32A   | 20  | 0       | **42**         |
| cXale SmartPDU 47HE 3P-32A   | 21  | 0       | **47**         |
| Dual SmartPDU 2HE            | 22  | 2       | 4 (horizontal) |
| SmartPDU 1P-16A              | 23  | 0       | **42**         |
| SmartPDU 1P-32A              | 24  | 0       | **42**         |

Kentix-Quelle: SmartPDU 40HE = 178cm = 40HE → passt ab **42HE-Rack**.

### Kentix SmartPDU — Intelligente PDU (kein einfacher Stromverteiler)

| Funktion                  | Detail                                                      |
|---------------------------|-------------------------------------------------------------|
| Strommessung              | MID-geeicht pro Outlet — gesetzlich für Abrechnung zulässig |
| Schaltbare Outlets        | Remote Ein/Aus via REST-API oder KentixONE                  |
| Sensorik integriert       | Temp, Feuchte, Taupunkt, Vibration, Brandfrüherkennung      |
| RCM                       | Differenzstrommessung — DGUV V3 ohne Abschaltung            |
| Management-Versorgung     | PoE — bleibt bei Stromausfall aktiv (USV-gepufferter Switch)|
| A/B-Lastabgleich          | Dual-PDU erkennt einseitige Last sofort                     |
| Racksicherheit            | RFID Rack-Hebel (DoorLock-RA) direkt anschließbar           |
| Software                  | KentixONE integriert — REST-API, LDAP, bis 100 PDUs         |

**Für KAiTix relevant:**
- REST-API → `kentix.py` kann Outlet-Messwerte abfragen (Watt, Ampere)
- Schaltbare Outlets → Remote-Reboot von Servern möglich
- RCM → Defekte Server-Netzteile frühzeitig erkennen
- Brandfrüherkennung → Auto-Ticket in KAiTix bei Alarm
- PoE-Management → PDU bleibt auch bei Stromausfall erreichbar

**Modellierung in KAiTix:**
- `typ = 'pdu'` in devices
- `api_url` + `api_key` für KentixONE REST-API
- `pdu_outlets` Tabelle mit `schaltbar=true`, `phase`, `steckdosentyp`
- `pdu_outlet_readings` für MID-geeichte Messwerte (Zeitreihe)

### USV — Wöhrle SVS (Berechnungsmodell)
Wöhrle ist das USV-Berechnungsmodell im Schema — kein zwingend
eingesetzter Hersteller. Die Simulation deckt ab:
- Σ Last aller Geräte
- Peak (Einschaltstrom)
- N+1 Kapazität
- Kaltstart-Check

**Konkrete Auslegung:**
- Last: ~15 kW (Phasen unausgeglichen, 12–17 kW)
- Schrank: Wöhrle WP2-R 40kW
- Module: 4× 10kW (N+1)
- N+1 Kapazität: 30 kW (ein Modul fällt aus)
- Kaltstart: 15 kW ≤ 30 kW ✓
- Reserve: 15 kW (100% Puffer)

### Riello (optional, eigenes Rack)
Riello Sentryum = modulare USV als eigenständiges Rack-Objekt.
Modellierung: eigener Eintrag in `racks` + `usv_units` mit rack_id.
Nicht im Server-Rack einbauen.

---

## IST-Situation Stromversorgung

### Topologie (aktuell)

```
Modulare N+1 USV (usv_units + usv_modules)
      │
      ▼
Unterverteilung / distribution_panel (1× vorhanden)
  ├── Schiene L1 (distribution_circuit) → ca. 12–17 kW
  ├── Schiene L2 (distribution_circuit) → ca. 12–17 kW
  └── Schiene L3 (distribution_circuit) → ca. 12–17 kW
      │
      ▼
Kentix SmartPDU 3-phasig (1× pro Rack, seitlich montiert)
  ├── L1-Outlets (6× C13 + 6× Cx)
  ├── L2-Outlets (6× C13 + 6× Cx)
  └── L3-Outlets (6× C13 + 6× Cx)
      │
      ▼
Server (immer 2 Netzteile)
  PSU1 → L1-Outlet
  PSU2 → L2- oder L3-Outlet
```

### Phasensituation

- Gesamtlast: ca. **12–17 kW** (Schätzung via TDP, nicht gemessen)
- Phasen **nicht ausgeglichen** — Imbalance vermutlich >10%
- Ursache: Geräte wurden ohne Phasenplanung angeschlossen
- Ziel: max. 10% Imbalance zwischen L1/L2/L3

### Warum eine PDU pro Rack (kein A+B)

N+1 USV mit einer Unterverteilung = Redundanz liegt in den USV-Modulen,
nicht in zwei getrennten Einspeisepfaden. Zwei PDUs wären nur sinnvoll
bei zwei getrennten USVs. Mit einer PDU hängen beide PSUs eines Servers
an verschiedenen Phasen derselben PDU.

### Ältere breite PDUs (Lagerbestand)

Neben den vertikalen cXale-Modellen gibt es ältere horizontale
PDU-Modelle auf Lager. Diese belegen echte HE im Rack und müssen
als normale Devices mit `u_hoehe > 0` modelliert werden.
Rack-Diagramme müssen entsprechend angepasst werden wenn diese
eingebaut werden.

---

## Bekannte Probleme & offene TODOs

### 1. TDP ≠ echter Stromverbrauch (KRITISCH)
`devices.tdp_watt` ist thermische Verlustleistung, nicht die echte
Leistungsaufnahme der Netzteile. Die USV-Berechnung ist damit
strukturell falsch.

**Lösung — drei Ebenen:**

```sql
-- Ebene 1: Datenblatt-Wert pro Netzteil
ALTER TABLE devices
  ADD COLUMN psu_count      TINYINT DEFAULT 2,
  ADD COLUMN psu_nennwatt   DECIMAL(8,2),
  ADD COLUMN last_pct       DECIMAL(5,1) DEFAULT 60.0;

-- Ebene 2: Echte Messwerte von Kentix PDU pro Outlet
CREATE TABLE pdu_outlet_readings (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  outlet_id   INT UNSIGNED NOT NULL,
  gemessen_am DATETIME(3) NOT NULL,
  watt        DECIMAL(8,2),
  ampere      DECIMAL(6,3),
  INDEX idx_outlet_time (outlet_id, gemessen_am),
  FOREIGN KEY (outlet_id) REFERENCES pdu_outlets(id)
);
```

**Priorisierung in der USV-Berechnung:**
1. Echte Kentix-Messung aus `pdu_outlet_readings` (wenn vorhanden)
2. `psu_nennwatt × (last_pct / 100)` (wenn konfiguriert)
3. `tdp_watt` als letzter Fallback

### 2. min_rack_hoehe fehlt / falsch in hardware_types.json
Alle 40HE-PDUs haben `min_rack_hoehe: 40` statt korrekt **42**.

**Fix:**
```python
fixes = {16: 42, 17: 42, 18: 42, 19: 42, 20: 42, 23: 42, 24: 42}
```
ID 21 (47HE) ist korrekt auf 47. ID 22 (2HE horizontal) klären.

### 3. Backend-Validierung min_rack_hoehe fehlt
Beim Einbauen einer PDU wird nicht geprüft ob
`hardware.min_rack_hoehe <= rack.hoehe_u`.

**Wo:** `app/api/endpoints/devices.py` — beim POST/PUT eines Devices
mit `u_hoehe=0` und `typ=pdu` prüfen:

```python
if hw.min_rack_hoehe and rack.hoehe_u < hw.min_rack_hoehe:
    raise HTTPException(400,
        f"PDU benötigt mind. {hw.min_rack_hoehe}HE-Rack "
        f"(Rack hat {rack.hoehe_u}HE)")
```

Gleiches beim PATCH von `racks.hoehe_u` — prüfen ob bereits verbaute
PDUs die neue Höhe unterschreiten würden.

### 4. Frontend-Warnung bei inkompatiblen PDUs fehlt
Im "Hardware einbauen"-Modal: rote Warnung wenn
`selectedHW.min_rack_hoehe > rack.hoehe_u`.
Einbauen-Button deaktivieren.

In Seitliche-Montage-Sektion: roten Rahmen + ⚠-Icon wenn PDU
zu groß für Rack.

### 5. alarm_ok Logik invertiert in kentix.py
```python
# FALSCH (aktuell):
alarm_ok = len(alarms) > 0
# RICHTIG:
alarm_aktiv = len(alarms) > 0
```

### 6. USV-Berechnung filtert nach rack_id statt circuit_id
Geräte werden aktuell per `rack_id` der USV zugeordnet — das ist
eine Vereinfachung. Korrekt wäre Zuordnung über `circuit_id` →
`distribution_circuits` → `distribution_panels` → `usv_units`.

### 7. Schema-Drift breite_mm (BUG)
`racks.breite_mm` existiert in MySQL (DEFAULT 600) aber fehlt im
SQLAlchemy ORM-Model und in den Pydantic-Schemas komplett.
API gibt breite_mm nie zurück — stille Datenverlust.

**Fix:**
```python
# app/models/rack.py
breite_mm: Mapped[Optional[int]] = mapped_column(Integer, default=600)
```
```python
# app/schemas/serverflow.py — RackBase
breite_mm: Optional[int] = 600
```

### 8. Strom-Kette ist bereits geschlossen (Korrektur)
`pdu_outlets` Tabelle existiert bereits im Schema.
Vollständige Kette:
Server → pdu_outlets.connected_device_id → PDU (device)
       → circuit_id → distribution_circuits → distribution_panels
       → usv_units
Problem liegt in der Berechnungslogik — sie ignoriert diesen Pfad
und geht direkt von Server.circuit_id aus.

### 9. Netzwerk-Kette — Interface-Merge statt FK-Patch
switch_hostname/switch_port sind Freitext ohne FK.
Lösung: ServerInterface + DevicePort zu einheitlichem Interface-Model
verschmelzen → Cable verbindet zwei Interfaces direkt.
(Erst nach stabilem Feature-Stand umsetzen — Breaking Change)

### 10. Phasen-Imbalance IST ~12–17 kW unausgeglichen (AKUT)
Aktuelle Last pro Phase ist unbekannt (TDP-Schätzung unzuverlässig)
und nicht ausgeglichen. Ziel: ≤10% Imbalance.

**Ursache:** Geräte wurden ohne Phasenplanung angeschlossen.
Outlets der PDU sind nicht systematisch L1/L2/L3 zugeordnet.

**Lösung:**
1. Echte Outlet-Messwerte von Kentix SmartPDU auslesen
   (`pdu_outlet_readings` — MID-geeicht)
2. Phasencheck auf Outlet-Ebene statt Device-Ebene rechnen
3. Empfehlung welche Geräte auf welche Phase umgesteckt werden sollen

**Berechnungsformel Phasen-Imbalance:**
```python
ideal    = gesamt_watt / 3
max_abw  = max(abs(w - ideal) for w in [L1, L2, L3])
imbalance = (max_abw / ideal) * 100  # Ziel: ≤ 10%
```

**Umsteckempfehlung:**
Gerät mit höchstem Einzelverbrauch von überlasteter Phase
auf schwächste Phase verschieben — iterativ bis Imbalance ≤10%.

---

## Backlog (priorisiert)

### Implementiert ✅ (seit letzter Session)
- [x] `virtual_machines` Tabelle + CRUD-API + Frontend-Seite
- [x] Runbook Orchestrator — Datenmodell, API, Frontend (Übersicht + Detailansicht)
- [x] `python-dotenv` in `app/core/config.py` + `alembic/env.py` integriert
- [x] Alembic-Migrationskette repariert (split-head behoben)
- [x] Tabellen per `Base.metadata.create_all()` + `alembic stamp head` initialisiert
- [x] `lazy="selectin"` für alle Runbook-Relationships (MissingGreenletError behoben)
- [x] `psu_count`, `psu_nennwatt`, `last_pct` zu devices hinzugefügt (Migration d02c996b4cfd)
- [x] `shutdown_priority`, `shutdown_delay_seconds`, `depends_on_device_id` zu devices

### Kurzfristig
- [ ] `min_rack_hoehe` in hardware_types.json korrigieren (40→42)
- [ ] Backend-Validierung `min_rack_hoehe` in devices.py
- [ ] Frontend-Warnung bei inkompatiblen PDUs
- [ ] `alarm_ok` → `alarm_aktiv` in kentix.py korrigieren
- [ ] Unterverteilung (distribution_panel) mit USV verknüpfen
- [ ] Phasen-Ist-Zustand erfassen (welches Gerät hängt an welchem Outlet/Phase)
- [ ] RackModal hoehe_u: Dropdown dynamisch aus hardware_types (nicht hardcodiert)
- [ ] RackModal: 8 Rittal-Varianten (600mm + 800mm) im Dropdown
- [ ] PDU-Auswahl im "Hardware einbauen" Modal nach rack.hoehe_u filtern
- [ ] devices.side Spalte (left/right) für 0U-PDU Seitenzuordnung
- [ ] Max. 1 vertikale PDU pro Seite pro Rack — Backend + Frontend
- [ ] PDU-Spalte im Rack-Diagramm füllt exakt rack.hoehe_u (nicht PDU-Höhe)
- [ ] Runbook: Gerät aus VM-Liste oder Device-Liste in Layer per Drag & Drop
- [ ] Runbook-Detailseite: Layer anlegen / bearbeiten / löschen
- [ ] Runbook-Execution: Step abhaken (check-off) im Frontend

### Mittelfristig
- [ ] `pdu_outlet_readings` Tabelle + Kentix-Poller erweitern
- [ ] Phasencheck auf Outlet-Ebene umstellen (statt TDP-Schätzung)
- [ ] Umsteckempfehlung bei Imbalance >10% (welches Gerät wohin)
- [ ] USV-Berechnung auf echte Outlet-Messwerte umstellen
- [ ] USV-Filter von rack_id auf circuit_id umstellen
- [ ] Batterielaufzeit-Berechnung (`kapazitaet_kwh` in usv_units)
- [ ] Rittal-Racks als Modelle im Hardware-Katalog anlegen
- [ ] Ältere horizontale PDUs (Lagerbestand) im Katalog anlegen
- [ ] VM-Seite: Abhängigkeitsgraph (depends_on_vm_id) visualisieren

### Langfristig
- [ ] Ausfallszenarien-Simulation (welches USV-Modul fällt aus?)
      - Interaktiver "Was-wäre-wenn"-Modus in der Topologie (Phasen-/USV-/PDU-Ausfall)
      - Visualisierung der betroffenen Geräte (Rot = stromlos, Gelb = redundante PSU, Grün = unbetroffen)
      - Chronologische Shutdown-Sequenzierung basierend auf `shutdown_priority`, `shutdown_delay_seconds` und `depends_on_device_id`
- [ ] Lasthistorie-Chart aus pdu_outlet_readings
- [ ] ~~iDRAC/iLO-Integration~~ — nicht relevant, reines Doku-Tool
- [ ] SNMP/LLDP-Discovery für automatische Topologie
- [ ] **E-Plan / Einlinienschaltbild Generator** — SVG-Stromlaufplan aus KAiTix-Daten
- [ ] **Leistungsbeschreibung / Angebots-Export** — PDF/Word aus KAiTix-Daten

---

## Datenfluss Strom (Ziel-Architektur)

```
Wöhrle USV (usv_units + usv_modules)
    │
    ▼
distribution_panels → distribution_circuits (L1/L2/L3)
    │
    ▼
Kentix SmartPDU (devices, u_hoehe=0, seitlich im Rittal-Rack)
    │  pdu_outlets → pdu_outlet_readings (MID-geeicht, Echtmessung)
    │
    ▼
Server PSU1 + PSU2 (devices, psu_count=2, psu_nennwatt)
```

---

## Modellierungsregeln (für Agenten)

1. Kentix SmartPDU 40HE/47HE → immer `u_hoehe=0`, `u_position=null`
2. Kentix PDU → min_rack_hoehe=42 (40HE) oder 47 (47HE)
3. Kentix PDU → `api_url` + `api_key` pflegen — REST-API wird aktiv genutzt
4. Kentix PDU → `pdu_outlets` mit `schaltbar=true`, Phase und Steckdosentyp
5. Riello USV → eigener Eintrag in `racks`, nicht als Device
6. Wöhrle → nur Berechnungsmodell, kein zwingender Hersteller
7. `tdp_watt` ist Fallback — `psu_nennwatt × last_pct` bevorzugen
8. Echte Leistung kommt aus `pdu_outlet_readings` (MID-geeicht von Kentix)
9. Alle Server haben 2 Netzteile (PSU1 und PSU2 an verschiedene Phasen)
10. Eine PDU pro Rack (N+1 liegt in USV-Modulen, nicht in zwei PDUs)
11. Ältere horizontale PDUs → `u_hoehe > 0`, normale HE-Belegung
    Beispiel: Kentix Dual SmartPDU 3P-32A = 2HE horizontal
    → normales Einbau-Modal, NICHT 0U-Seitenbereich
    → 0U-Modal zeigt NUR PDUs mit u_hoehe=0
12. Nur MySQL — kein PostgreSQL, SQLite, SurrealDB
13. Agenten dürfen keine eigenständigen DBs anlegen
14. Jeder Agent-Prompt muss mit AGENT.md-Lesen beginnen —
    sonst droht falscher Kontext (CabellistPro, FalkorDB, etc.)
15. hoehe_u im RackModal immer dynamisch aus hardware_types ableiten —
    keine hardcodierten HE-Werte
16. PDU-Auswahl beim Einbauen immer gegen rack.hoehe_u filtern:
    nur PDUs mit min_rack_hoehe <= rack.hoehe_u sind wählbar
17. Pro Rack-Seite (0UL / 0UR) maximal eine vertikale PDU
18. 0U-PDU Spalte im Diagramm immer rack.hoehe_u hoch zeichnen
19. **VMs sind Dokumentation, keine Live-Daten** — `virtual_machines` Tabelle,
    kein Agent darf dort Live-Metriken schreiben
20. **Runbooks**: `runbook_devices` kann `device_id` ODER `vm_id` ODER `freitext`
    enthalten — niemals alle drei gleichzeitig zwingend
21. **SQLAlchemy async**: Alle neuen Router-Relationships brauchen `lazy="selectin"`
    oder explizites `selectinload()` im Query — kein lazy default in async Context
22. **`.env` immer prüfen**: Fehlt `.env`, schlägt alles mit `Access denied for root` fehl.
    Vorlage: `DATABASE_URL=mysql+aiomysql://kaitix:kaitix@127.0.0.1:3306/kaitix`

---

## Security (bewusste Entscheidungen)

- **Kein Auth** — internes Tool, kein Login, keine Rollen
- **Kein JWT, kein LDAP, keine Sessions**
- **CORS** — localhost:5175/5176/5177 + LAN-IP erlaubt (in `ALLOWED_ORIGINS` in `.env`)
- **.env in .gitignore** — Secrets nie ins Git
- **Audit-Log** — geaendert_von (Freitext) + geaendert_am Timestamp
- **Username** — Freitext im Frontend, in localStorage gespeichert
  Einmalig eingeben → bei jeder Änderung automatisch mitgeschickt
  Kein Passwort, kein Token, kein Server-seitiges Auth
  Anzeige z.B. oben rechts: "Sitzung: Andreas" (editierbar)
- **HTTPS** — Nginx reverse proxy wenn über LAN erreichbar
- SQL Injection: durch SQLAlchemy ORM abgedeckt ✓
- Input Validation: durch Pydantic abgedeckt ✓

---

## Pflicht-Präfix für jeden Agenten-Prompt

```
PROJEKT: KAiTix — ~/Projekte/aktiv/KAiTix
STACK: FastAPI + SQLAlchemy 2.x async + aiomysql + Svelte 5 (kein TypeScript) + MySQL (DB: kaitix)
LIES ZUERST: ~/Projekte/aktiv/KAiTix/AGENT.md
DANN ERST: Aufgabe umsetzen — kein anderer Kontext gilt.
```

### Neue Module (Stand 2026-05-25)

| Route / Prefix         | Datei(en)                                          | Beschreibung                          |
|------------------------|----------------------------------------------------|---------------------------------------|
| `/api/v1/virtual-machines` | `app/domains/hardware/routers/virtual_machines.py` | VM-Dokumentation CRUD                 |
| `/api/v1/runbooks`     | `app/domains/runbooks/router.py`                   | Runbook + Layer + Device CRUD         |
| `/api/v1/executions`   | `app/domains/runbooks/router.py`                   | Ausführungen + Step-Check             |
| Frontend `/virtual-machines` | `frontend/src/routes/virtual-machines/+page.svelte` | VM-Übersicht + Modal               |
| Frontend `/runbook`    | `frontend/src/routes/runbook/+page.svelte`         | Runbook-Liste + Neu-Anlegen           |
| Frontend `/runbook/[id]` | `frontend/src/routes/runbook/[id]/+page.svelte`  | Runbook-Detailansicht (Layers/Steps)  |

---

## Nix Dev Environment (Stand 2026-05-25)

### Architektur

```
Ubuntu (System-Basis)          Nix Single-User (Dev-Umgebungen)
─────────────────────          ────────────────────────────────
MySQL 8 als systemd-Service    Python 3.12 + Node.js 22 (shell.nix)
systemd, apt, GUI-Apps         direnv: Auto-Aktivierung beim cd
zsh als Login-Shell            common.nix: geteilte Pakete alle Projekte
```

### Setup-Dateien

| Datei | Pfad | Zweck |
|-------|------|-------|
| `shell.nix` | `~/Projekte/aktiv/KAiTix/shell.nix` | Projekt-Dev-Shell |
| `common.nix` | `~/Projekte/nix/common.nix` | Geteilte Pakete |
| `.envrc` | `~/Projekte/aktiv/KAiTix/.envrc` | `use nix` — direnv Trigger |

### Pakete (aus common.nix)

- `python312` — Python Runtime
- `nodejs_22` — Node.js + npm (Svelte 5)
- `openssl` — SSL für PyMySQL/httpx
- `pkg-config` — Build-Helper
- `mariadb-connector-c` — Fallback C-Connector
- `git`, `curl`, `jq` — Standard-Tools

### Workflow

```bash
# Automatisch beim cd in das Verzeichnis:
cd ~/Projekte/aktiv/KAiTix
# → direnv lädt automatisch: "direnv: loading .envrc"
# → nix-shell startet: "=== KAiTix Dev Shell ==="
# → Python 3.12 + Node 22 verfügbar

# venv weiterhin manuell aktivieren (direnv aktiviert es NICHT):
source .venv/bin/activate

# Entwicklung starten:
make dev-all   # Backend (Port 8003) + Frontend parallel
```

### Wichtige Regeln für Agenten

- **nodejs_22** (nicht nodejs_20 — EOL!)
- **zsh** als Shell (nicht bash — seit dieser Session migriert)
- **direnv** Hook in `~/.zshrc`: `eval "$(direnv hook zsh)"`
- **venv** wird NICHT automatisch aktiviert — manuell nötig
- **`nix-shell`** muss nicht manuell gestartet werden — direnv übernimmt das
- **Shell-Hook** setzt `LD_LIBRARY_PATH` für Ubuntu-Kompatibilität (openssl, mariadb)

### CDP / Browser (für Playwright/E2E)

```bash
flatpak run com.google.Chrome -- --remote-debugging-port=9222
```

**NIEMALS** Brave/Vivaldi für CDP nutzen — nur Chrome!

---

## Memory-Import

### Lokale Kopie einspielen
```bash
cp ~/Downloads/AGENT.md ~/Projekte/aktiv/KAiTix/AGENT.md
```

### Für Gemini / andere Agenten
Inhalt als Datei anhängen oder direkt in den Prompt einfügen:
```bash
cat ~/Projekte/aktiv/KAiTix/AGENT.md
```

### Für Claude
Claude Memory wird über das Chat-Interface gesetzt — nicht per Bash.
Nach jeder AGENT.md-Aktualisierung Claude im Chat sagen:
> "Aktualisiere dein Memory mit dem neuen Stand der AGENT.md"

Claude liest dann die relevanten Abschnitte und speichert sie.

> Diese Datei wird bei jeder größeren Architekturentscheidung
> aktualisiert. Letzter Stand: `ls -la AGENT.md`

## Rittal Hardware-Katalog Seed (data/hardware_types.json)

Nach aktuellem Maximum (ID 24) folgende 8 Einträge ergänzen:

```python
rittal_racks = [
  {"id":25,"name":"Rittal VX IT 42HE 600mm","kategorie":"rack","hersteller":"Rittal","modell":"VX IT 42HE 600mm","u_hoehe":42,"breite_mm":600,"tiefe_mm":1000,"min_rack_hoehe":0,"tdp_watt":None,"bemerkung":"SmartPDU 40HE möglich, eng"},
  {"id":26,"name":"Rittal VX IT 42HE 800mm","kategorie":"rack","hersteller":"Rittal","modell":"VX IT 42HE 800mm","u_hoehe":42,"breite_mm":800,"tiefe_mm":1000,"min_rack_hoehe":0,"tdp_watt":None,"bemerkung":"SmartPDU 40HE empfohlen"},
  {"id":27,"name":"Rittal VX IT 47HE 600mm","kategorie":"rack","hersteller":"Rittal","modell":"VX IT 47HE 600mm","u_hoehe":47,"breite_mm":600,"tiefe_mm":1000,"min_rack_hoehe":0,"tdp_watt":None,"bemerkung":"SmartPDU 47HE möglich, eng"},
  {"id":28,"name":"Rittal VX IT 47HE 800mm","kategorie":"rack","hersteller":"Rittal","modell":"VX IT 47HE 800mm","u_hoehe":47,"breite_mm":800,"tiefe_mm":1000,"min_rack_hoehe":0,"tdp_watt":None,"bemerkung":"SmartPDU 47HE empfohlen"},
  {"id":29,"name":"Rittal TS IT 42HE 600mm","kategorie":"rack","hersteller":"Rittal","modell":"TS IT 42HE 600mm","u_hoehe":42,"breite_mm":600,"tiefe_mm":1000,"min_rack_hoehe":0,"tdp_watt":None,"bemerkung":"SmartPDU 40HE möglich, eng"},
  {"id":30,"name":"Rittal TS IT 42HE 800mm","kategorie":"rack","hersteller":"Rittal","modell":"TS IT 42HE 800mm","u_hoehe":42,"breite_mm":800,"tiefe_mm":1000,"min_rack_hoehe":0,"tdp_watt":None,"bemerkung":"SmartPDU 40HE empfohlen"},
  {"id":31,"name":"Rittal TS IT 47HE 600mm","kategorie":"rack","hersteller":"Rittal","modell":"TS IT 47HE 600mm","u_hoehe":47,"breite_mm":600,"tiefe_mm":1000,"min_rack_hoehe":0,"tdp_watt":None,"bemerkung":"SmartPDU 47HE möglich, eng"},
  {"id":32,"name":"Rittal TS IT 47HE 800mm","kategorie":"rack","hersteller":"Rittal","modell":"TS IT 47HE 800mm","u_hoehe":47,"breite_mm":800,"tiefe_mm":1000,"min_rack_hoehe":0,"tdp_watt":None,"bemerkung":"SmartPDU 47HE empfohlen"},
]
```

Zusätzliche Validierungsregel:
- Rack mit breite_mm=600 + Zero-U PDU eingebaut → Frontend Warnung
- Rack mit breite_mm=800 + Zero-U PDU → OK
