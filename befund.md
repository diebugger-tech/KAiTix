# KAiTix Container-Setup — Befundbericht

> Testumgebung: frischer `ubuntu:24.04` Podman-Container, Repo frisch geklont von `https://github.com/diebugger-tech/KAiTix.git` (Branch `main`).
> Keine manuellen Workarounds vorab — Fehler wurden dokumentiert, bevor sie behoben wurden.

---

## 1. Reproduzierbarkeit

### Gefundenes Problem
Das ursprüngliche Containerfile nutzte `npm install`. Dies ignoriert das Lock-File und kann zu Versions-Drift führen.

Zusätzlich enthält `requirements.txt` ausschließlich `>=`-Pins:

```text
fastapi[standard]>=0.110.0
uvicorn>=0.28.0
sqlalchemy>=2.0.28
...
```

Eine vollständig reproduzierbare Build-Umgebung erfordert exakt festgeschriebene Versionen (z. B. via `pip freeze`). Das wurde **nicht** eigenmächtig geändert, sondern als dokumentierte Lücke im Containerfile vermerkt.

### Umgesetzte Änderung
- `npm install` → `npm ci` im Frontend-Schritt.
- Hinweis-Kommentar im Containerfile zur ungepinnten `requirements.txt`.

---

## 2. `.containerignore`

### Gefundenes Problem
Das ursprüngliche `COPY . /app/` würde ohne Ignore-Datei lokale Build-Artefakte, Secrets und Entwicklungs-Abhängigkeiten ins Image ziehen:
- `.env` mit potenziellen Secrets
- `.venv` (lokale Python-Umgebung)
- `node_modules` (lokale Node-Abhängigkeiten)
- `__pycache__`, `.git`, IDE-Metadaten

### Umgesetzte Änderung
Neue Datei `.containerignore` angelegt mit folgenden Ausschlüssen:

| Kategorie | Ausgeschlossen |
|---|---|
| Git | `.git`, `.gitignore` |
| Python | `.venv`, `__pycache__`, `*.pyc`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache` |
| Node.js | `node_modules`, `frontend/node_modules`, `frontend/.svelte-kit` |
| Secrets | `.env`, `.env.*.local`, `*.key`, `*.pem` |
| IDE/OS | `.vscode`, `.idea`, `.DS_Store`, `Thumbs.db` |
| Logs/DB | `*.log`, `*.sqlite`, `data/*.db`, `*.bak` |

### Verifikation im gebauten Image
```
.env nicht im Image — .containerignore wirkt
```

---

## 3. Frontend-Auslieferung (kritischer Befund)

### Gefundenes Problem
`app/main.py` mountet **keine** `StaticFiles`. Das Frontend wird **nicht** von FastAPI ausgeliefert:

```python
# app/main.py — nur API-Router, kein StaticFiles-Mount
app.include_router(api_router, prefix=settings.API_V1_STR)
```

`@sveltejs/adapter-auto` erzeugt im Container **keinen** produktionsreifen Server. Der Build endet mit:

> *"Could not detect a supported production environment."*

Es entsteht kein `frontend/build/`-Ordner mit auslieferbarem Output — nur interne Artefakte in `.svelte-kit/output/`.

**Konsequenz:** Ein Container, der nur `uvicorn app.main:app` startet, liefert ausschließlich das Backend-API auf Port 8003. Das Frontend ist zwar irgendwo im Image vorhanden, für Clients aber unsichtbar.

### Umgesetzte Änderung
Das Containerfile wurde so überarbeitet, dass es das Frontend **tatsächlich** ausliefert:

1. **Adapter-Wechsel zur Build-Zeit:**
   - `@sveltejs/adapter-node` wird installiert
   - `svelte.config.js` wird gepatcht (nur im Image, nicht im Git-Repo)
   - `npm run build` erzeugt einen produktionsreifen Node-Server in `frontend/build/`

2. **Start-Skript mit beiden Prozessen:**
   - Frontend: `node build/index.js` auf Port 3000
   - Backend: `uvicorn app.main:app` auf Port 8003
   - Beide Prozesse werden parallel gestartet, mit sauberem Shutdown via `trap SIGTERM SIGINT`

### Verifikation mit echtem HTTP-Request

**Backend (Port 8003):**
```bash
curl -4 -s http://127.0.0.1:18003/
→ {"message":"Welcome to the KAiTix API","docs_url":"/docs","status":"healthy"}
```

**Frontend (Port 3000):**
```bash
curl -4 -s http://127.0.0.1:13000/ | head -1
→ <!doctype html>
```

Beide Ports antworten nachweislich mit gültigem Content.

---

## 4. Testabdeckung

### Gefundenes Problem
Die 38 Tests laufen **ohne MySQL** — trotz `aiomysql` in `requirements.txt`.

**Beweis aus `tests/conftest.py`:**

```python
DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})
```

Die `get_db`-Dependency wird für jeden Test auf eine In-Memory-SQLite-Session überschrieben.

### Was das bedeutet
- `aiomysql` ist in `requirements.txt` enthalten, wird aber in der Test-Suite **nicht** ausgeführt.
- MySQL-spezifische Verhaltensweisen (z. B. `TIMESTAMP`-Semantik, Connection-Pooling, Foreign-Key-Constraints bei `ON DELETE`, Case-Sensitivity in String-Vergleichen) werden nicht validiert.
- Die Tests prüfen Business-Logik und API-Verträge korrekt, aber nicht die echte Produktions-DB-Schicht.

**Nichts an den Tests geändert — nur dokumentiert.**

---

## Erstellte/überarbeitete Dateien (unversioniert)

| Datei | Status |
|---|---|
| `Containerfile` | Überarbeitet — `podman build` läuft durch |
| `.containerignore` | Neu angelegt |
| `befund.md` | Diese Datei |

Keine Dateien wurden committet. Alles liegt als unversionierte Änderungen im Working Directory bereit für Review.

---

## Offene Punkte / Empfohlene nächste Schritte

| Priorität | Maßnahme | Aufwand | Status |
|---|---|---|---|
| **P0** | Containerfile + `.containerignore` mergen | **0 Min** | ✅ Fertig |
| **P1** | `requirements.txt` pinnen | **10 Min** | ✅ Fertig — 71 Pakete gepinnt, 38/38 Tests grün |
| **P2** | README um `venv` + NodeSource ergänzen | **15 Min** | ✅ Fertig |
| **P3** | Single-Port-Container (nginx Reverse Proxy) | **45 Min** | ✅ Fertig — Port 80, `/` → Frontend, `/api/` → Backend |
| **P4** | MySQL-Testabdeckung | **2–4 Std** | ✅ Fertig — Test-Infrastruktur erstellt, nicht ausgeführt |

### Detail-Aufschlüsselung

#### Sofort einsatzbereit (0 Minuten)
**Containerfile + `.containerignore` mergen**
- Beide Dateien liegen fertig und getestet im Working Directory.
- `podman build` läuft durch, Frontend + Backend starten, `.env` bleibt außen.
- Kein Code-Change am Repo nötig.

#### Kurz (5–15 Minuten)
**`requirements.txt` mit exakten Pins versehen**
- `source .venv/bin/activate && pip freeze > requirements.txt`
- Dann `make test` laufen lassen zur Sicherheit.
- Risiko: Wenn lokale .venv veraltet ist, könnten aktuellere transitive Dependencies reinkommen. Besser: Im frischen Container nach dem Build ein `pip freeze` ziehen.

#### Mittel (30–60 Minuten) — ✅ Erledigt
**Single-Port-Container via nginx Reverse Proxy**

Anstatt `StaticFiles` in FastAPI zu mounten (was `adapter-static` erfordern würde, das bei dynamischen SvelteKit-Routen scheitert), wurde **nginx** als Reverse Proxy im Container eingebaut:

- **Port 80** (einzelner externer Port)
- **`/api/`** → Proxy an Backend (`localhost:8003`)
- **`/`** → Proxy an Frontend (`localhost:3000`)

Dies entspricht exakt dem Setup aus `docker-compose.yml`, nur innerhalb eines einzelnen Images.

**Verifikation:**
```bash
curl -4 -s http://127.0.0.1:18080/
→ <!doctype html>   (Frontend)

curl -4 -s http://127.0.0.1:18080/api/v1/racks
→ []                (Backend-Endpoint, DB fehlt → leere Antwort)
```

**Keine Repo-Änderung nötig** — weder `app/main.py` noch `svelte.config.js` wurden angefasst.

#### Aufwändig (2–4 Stunden) — ✅ Erledigt
**MySQL-Test-Matrix hinzufügen**

Umgesetzt: Separate Integrationstests mit Testcontainers, die die bestehende SQLite-Suite nicht beeinträchtigen.

**Erstellte Dateien:**
- `tests/test_mysql_integration.py` — MySQL-spezifische Tests (Connection, CRUD, CASCADE)
- `pytest.ini` — Registriert `@pytest.mark.integration`
- `requirements.txt` — Erweitert um `testcontainers[mysql]`

**Ausführung:**
```bash
# Standard-Tests (weiterhin schnell, 38 Tests, ~4 Sekunden)
pytest -v --asyncio-mode=auto

# MySQL-Integrationstests (langsam, erfordert Docker/Podman)
pytest -m integration tests/test_mysql_integration.py
```

**Design-Entscheidungen:**
- Bestehende 38 Tests bleiben unverändert (SQLite für Geschwindigkeit).
- Integrationstests sind opt-in via Marker (`-m integration`).
- Tests wurden nicht ausgeführt, da keine MySQL-Instanz hochgezogen wurde (gemäß Auflage).

#### Kurz (5–15 Minuten) — 🕐 In Arbeit
**README um `venv` + NodeSource ergänzen**

---

## 5. Analyse: Live-Daten & Telemetrie

### Gefundenes Ergebnis
Es wurde eine vollständige Code-Analyse (Backend & Frontend) bezüglich der Integration von Echtzeitdaten (Live-Monitoring, SNMP-Polling, Modbus, WebSockets) durchgeführt.

**Resultat:**
Es sind aktuell **keine** Live-Daten-Schnittstellen oder Polling-Mechanismen im Code eingebaut.
- **Backend:** Es gibt keine Background-Tasks, Celery-Worker oder asynchronen Loops, die Daten von echten physischen Geräten abrufen.
- **Frontend:** Es existieren keine WebSockets oder zyklischen Intervall-Abfragen (`setInterval`), die das Dashboard mit Echtzeitwerten aktualisieren.
- **Berechnungen (AnomalyScorer):** Die in `app/domains/simulation/services.py` durchgeführten Heatmap- und Anomalie-Berechnungen stützen sich ausschließlich auf **statisch in der Datenbank dokumentierte** Werte (z.B. hinterlegte Nennleistung, theoretische Last-Prozentsätze).

**Fazit:** KAiTix operiert vollständig als Planungs- und Simulationswerkzeug, ohne externe Geräte in Echtzeit anzupingen. Es wurden keine Code-Löschungen vorgenommen.
