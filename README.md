# KAiTix ServerFlow ⚡️

**Professional Datacenter Power & Hardware Documentation (DCIM) — Open Core**

[![License: AGPL-v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![SvelteKit 5](https://img.shields.io/badge/SvelteKit-5.0--next-ff3e00.svg)](https://svelte.dev/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4%2B-38bdf8.svg)](https://tailwindcss.com/)

KAiTix ServerFlow ist eine hochperformante, webbasierte **Open-Core B2B-Software** zur lückenlosen physikalischen Dokumentation von IT-Infrastrukturen und Stromnetzen in Rechenzentren (DCIM). Das System modelliert Racks, PDUs, Server, Switche und deren Verkabelungen als mathematisch gerichteten Graphen. 

Im Gegensatz zu klassischen Excel-Listen oder unübersichtlichen Monitoring-Tools ist KAiTix eine reine **Dokumentations- und Simulationslösung** (kein Live-Polling über SNMP/API, keine störenden Background-Tasks), die eine exakte Planungsbasis für RZs bietet.

---

## 🚀 Die 4 Säulen von KAiTix

### 1. Eaton & Wöhrle USV-Simulation
Planung und Dimensionierung der Ausfallsicherheit auf modularer Basis:
* **Modulare USV-Systeme:** Detaillierte Abbildung von Systemen wie der **Wöhrle SVS** oder **Eaton** USV-Schränken.
* **N+1 Redundanz-Kalkulation:** Automatische Ermittlung der benötigten Leistungsmodule und Batterietracks basierend auf der dokumentierten Maximallast (TDP/Watt) der Racks.
* **Wartungsumgehung (MBS):** Simulation des manuellen Service-Bypasses. Bricht eine Phase (L1/L2/L3) weg, berechnet KAiTix über Graphentraversierung im Backend in Echtzeit, welche Server-Netzteile stromlos werden und ob die Redundanz erhalten bleibt.

### 2. Kentix SmartPDU Integration
Volle Unterstützung für moderne, messende 0U/1U Power Distribution Units (PDUs):
* **Phasen-Balancing:** Erfassung der Phasenbelegung (L1, L2, L3) pro PDU-Steckdose zur Vermeidung von Schieflasten im TN-S-Netz.
* **Rack-Höhenvalidierung:** Automatische Sperrung von inkompatiblen vertikalen PDUs (z.B. Deaktivierung von 47HE 0U-PDUs in einem 42HE Rittal Rack).
* **Steckdosengenaue Zuordnung:** Dokumentation von C13, C19 und Schuko-Anschlüssen inklusive schaltbarer Relais-Zuordnung.

### 3. CAD E-Plan Stromlaufplan (DIN EN 61082-1)
Erstellung allpoliger Stromlaufpläne direkt aus der Datenbank:
* **Vektorgrafiken (SVG):** Dynamische, pixelgenaue Generierung von Schaltplänen.
* **Normkonforme Darstellung:** Abbildung von Sicherungselementen (NH-Trenner, Leitungsschutzschalter), Einspeiseklemmen, USV-Blöcken und Racks als Ortskästen.

### 4. End-to-End Kabelmanagement & EPLAN Import
Lückenlose Rückverfolgbarkeit aller Daten- und Stromwege:
* **EPLAN CSV-Schnittstelle:** Automatisierter Import allpoliger Verbindungslisten mit flexibler Spaltenzuordnung, Live-Vorschau und Port-Typ-Mapping.
* **Kabelverfolgung (Trace):** Abfrage des vollständigen Verbindungsweges über mehrere Stationen (z. B. `Switch-Port -> Patchpanel -> Server-Port`).
* **Multi-Format Export:** Bereitstellung vollständiger Kabellisten als XLSX (Excel), ODS (Calc) oder CSV über einen integrierten Export-Service.

---

## 🛡️ Lizenz & Open Core Modell

Dieses Projekt steht unter der **GNU Affero General Public License v3 (AGPL-3.0)**. 

### Was bedeutet das für dich?
* **Freie Nutzung:** Du darfst KAiTix Core kostenlos herunterladen, hosten, modifizieren und im eigenen Unternehmen einsetzen.
* **Copyleft-Pflicht:** Wenn du den Code modifizierst und als Webservice anbietest (SaaS), musst du den modifizierten Quellcode unter derselben AGPL-3.0 Lizenz öffentlich bereitstellen. Dies verhindert, dass kommerzielle IT-Dienstleister KAiTix ohne Beteiligung der Community weiterverkaufen.
* **Enterprise Edition:** Für proprietäre Enterprise-Integrationen (wie Active Directory/LDAP, unlimitierte PDF-Reportings oder bidirektionale Synchronisierung mit dem `hv-gateway` Hardware-Interface) bieten wir eine kommerzielle Lizenz an.

---

## 🛠️ Systemanforderungen & Installation

### Voraussetzungen nach Betriebssystem

#### 1. Linux & NixOS (Empfohlen)
KAiTix ist für Linux optimiert. Unter NixOS ist eine deklarative Entwicklungsumgebung via Flakes/nix-shell vorkonfiguriert.
* **Pakete:** Python 3.12+, Node.js (v20+), MariaDB/MySQL-Bibliotheken, `pkg-config`, `openssl`.
* **Nix-Shell starten:**
  ```bash
  nix-shell
  # Installiert automatisch python312, mariadb-connector-c, openssl, pkg-config und setzt Umgebungsvariablen.
  ```

#### 2. Apple macOS
Installation der Abhängigkeiten via Homebrew:
```bash
brew install python@3.12 node mariadb pkg-config openssl
export PATH="/opt/homebrew/opt/mysql-client/bin:$PATH"
```

#### 3. Microsoft Windows
Für die Ausführung unter Windows werden folgende Komponenten benötigt:
1. **Python 3.12+:** Installer von python.org (Haken bei "Add Python to PATH" setzen).
2. **Node.js (LTS):** Installer von nodejs.org.
3. **C-Compiler / Build Tools:** Visual Studio Build Tools (C++ Clang Compiler) für die Kompilierung des MySQL-Clients (pymysql/aiomysql) oder alternativ Nutzung einer lokalen SQLite-Datenbank.
4. **Git:** Git for Windows zur Versionsverwaltung.

---

## ⚙️ Schritt-für-Schritt Installation

1. **Repository klonen:**
   ```bash
   git clone https://github.com/diebugger-tech/KAiTix.git
   cd KAiTix
   ```

2. **Virtuelle Python-Umgebung einrichten:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. **Abhängigkeiten installieren:**
   ```bash
   make install  # Installiert alle Python-Bibliotheken aus requirements.txt
   ```

4. **Konfiguration (`.env`):**
    Kopiere die `.env.example` in eine neue `.env`-Datei und passe die Datenbank-URL an:
   ```bash
   cp .env.example .env
   ```
   *Standardmäßig ist KAiTix für eine lokale MySQL/MariaDB-Datenbank vorkonfiguriert. Für Testzwecke kann auch eine SQLite-Datenbank verwendet werden (`DATABASE_URL=sqlite+aiosqlite:///./kaitix.db`).*

5. **Datenbank-Migrationen ausführen:**
   ```bash
   make migrate-apply
   ```

6. **Frontend-Abhängigkeiten installieren:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

7. **Anwendung starten:**
   ```bash
   make dev-all
   ```
   * KAiTix Backend läuft auf: `http://localhost:8003`
   * KAiTix Frontend läuft auf: `http://localhost:5175`

---

## 📂 Makefile Befehlsreferenz

Verwende das integrierte Makefile für alle Entwicklungsaufgaben:

| Befehl | Beschreibung |
|---|---|
| `make help` | Zeigt alle verfügbaren Makefile-Targets an. |
| `make dev` | Startet nur das FastAPI-Backend (Port 8003) mit Auto-Reload. |
| `make dev-frontend` | Startet nur das SvelteKit-Frontend (Port 5175) im Dev-Modus. |
| `make dev-all` | Startet Backend und Frontend parallel. |
| `make install` | Installiert die Python-Pakete in der aktiven virtuellen Umgebung. |
| `make test` | Führt die gesamte pytest-Testsuite (11 Tests) asynchron aus. |
| `make lint` | Prüft den Code auf Syntax- und Typfehler via `ruff` und `mypy`. |
| `make format` | Formatiert den Python-Code und behebt Fehler automatisch via `ruff`. |
| `make migrate-create message="..."` | Erstellt eine neue Alembic-Datenbankmigration. |
| `make migrate-apply` | Wendet alle ausstehenden Migrationen auf der Datenbank an. |
| `make db-shell` | Öffnet eine interaktive MySQL-Shell für die konfigurierte Datenbank. |
| `make clean` | Löscht alle temporären Dateien (`__pycache__`, `.pytest_cache`, `.bak` Backups). |

---

## 🏷️ GitHub-Listing & Kentix Topic Tagging

Um das Projekt auf GitHub optimal unter der **Kentix**-Entwicklungscommunity zu platzieren, füge der Repository-Einstellungsseite folgende Tags (Topics) hinzu:
* `kentix` (Pflicht)
* `smartpdu`
* `dcim`
* `datacenter-infrastructure`
* `power-simulation`
* `eplan`
* `sveltekit`
* `fastapi`

Dadurch wird KAiTix von anderen Entwicklern und RZ-Betreibern, die nach Kentix-Integrationen oder DCIM-Dokumentationswerkzeugen suchen, sofort gefunden.
