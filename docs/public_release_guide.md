# KAiTix Open-Source Release & Roadmap Guide 🚀

Dieses Dokument dient als Leitfaden für die Veröffentlichung des KAiTix-Repositories auf GitHub unter `https://github.com/diebugger-tech/KAiTix` und beschreibt strategische sowie technische Verbesserungen für die Zukunft.

---

## 📦 1. Vorbereitung des Repositories (Git-Isolierung)

Da das gesamte Home-Verzeichnis (`/home/andreas`) derzeit als Git-Repository initialisiert ist, ist es **dringend ratsam, KAiTix als eigenständiges, isoliertes Git-Repository zu initialisieren**, um eine unbeabsichtigte Veröffentlichung privater Dateien zu verhindern.

### Vorgehensweise zur sauberen Initialisierung:

```bash
# 1. In das KAiTix-Projektverzeichnis wechseln
cd /home/andreas/Projekte/aktiv/KAiTix

# 2. Ein eigenständiges Git-Repository im Unterordner initialisieren
git init

# 3. Sicherstellen, dass die .gitignore existiert und konfiguriert ist
# (Stellt sicher, dass .env, .venv, *.bak, und pycache ignoriert werden)
cat .gitignore

# 4. Alle Projektdateien dem neuen Index hinzufügen
git add -A

# 5. Ersten Commit erstellen
git commit -m "feat: initial open-source release of KAiTix Core v0.1.0"

# 6. Remote-Adresse hinzufügen
git remote add origin https://github.com/diebugger-tech/KAiTix.git

# 7. Auf den Haupt-Branch umbenennen und pushen
git branch -M main
git push -u origin main
```

> [!WARNING]
> Führe die obigen Befehle erst aus, wenn alle lokalen Änderungen aus den `feature/agent-*`-Zweigen des übergeordneten Repositories zusammengeführt oder gesichert wurden, um Datenverlust zu vermeiden.

---

## 🏷️ 2. GitHub-Präsenz & Kentix-Listing

Um KAiTix sichtbar zu machen, insbesondere für Nutzer der **Kentix SmartPDUs** und Betreiber von Rechenzentren:

### A. Repository-Topics (Tags)
Füge in den GitHub-Einstellungen deines Repositories folgende Tags hinzu:
* `kentix`, `smartpdu`, `kentix-pdu` — für direkte Suchanfragen bezüglich Kentix-Hardware.
* `dcim`, `datacenter`, `rechenzentrum` — für IT-Infrastruktur-Planungstools.
* `eplan`, `stromlaufplan`, `cad` — zur Visualisierung von Stromlaufplänen.
* `sveltekit`, `fastapi`, `python`, `tailwindcss` — für den Tech-Stack.

### B. Readme-Optimierung
* Trage ein ansprechendes **Social Preview Image (Teaser-Bild)** in die GitHub-Einstellungen ein (z. B. einen Screenshot des CAD E-Plan-Views oder des USV-Bypass-Simulators).
* Verweise im README direkt auf die unterstützten Kentix SmartPDU-Modelle (**SmartPDU Vertikal 40HE 3P-16A**, etc.).

### C. Kentix Community-Beitrag
* Veröffentliche eine kurze Vorstellung deines Tools im **Kentix Partner- oder Developer-Forum** (falls vorhanden) oder teile es auf LinkedIn.
* Kontaktiere Kentix direkt (oder deren Support/Developer-Relations) mit dem Hinweis, dass es nun ein fertiges, freies Open-Source-Dokumentationstool für deren SmartPDUs gibt. Oft werden solche Tools gerne in Community-Ressourcen oder Repositories verlinkt.

---

## 💡 3. Zukünftige Ideen & Produktverbesserungen

Für die Weiterentwicklung von KAiTix zu einem vollwertigen B2B-Produkt empfehlen wir folgende nächste Schritte:

### 1. MBS Live-Sandbox (UI)
* **Konzept:** Ein interaktives Stromnetz-Cockpit im Frontend.
* **Feature:** Benutzer können per Schieberegler oder Klick einzelne Phasen (L1/L2/L3) oder USV-Module wegschalten und sehen visuell in Echtzeit am Rack-Diagramm, welche Server/Switche rot aufleuchten (ausfallen) und welche noch über redundante Pfade (Pfad B) versorgt werden.

### 2. Ein-Klick-Import von Kentix APIs (Optionaler Sync)
* **Konzept:** Obwohl KAiTix eine reine Dokumentationslösung ist, spart ein Import-Assistent viel Zeit.
* **Feature:** Eingabe der IP-Adresse und des API-Keys einer echten Kentix SmartPDU. Das Backend holt sich einmalig alle deklarierten Steckdosen und deren Namen und legt sie in der KAiTix-Datenbank an, ohne dass diese manuell eingetippt werden müssen.

### 3. Tauri-Container für Desktop & Offline-Nutzung
* **Konzept:** Viele RZ-Administratoren arbeiten offline oder in isolierten Management-Netzen ohne Docker/Server-Umgebungen.
* **Feature:** Verpackung von KAiTix als native Desktop-App (Tauri mit Rust-Backend und Svelte-Frontend). Dies ermöglicht eine portable Installation per `.exe` (Windows) oder `.app` (macOS), die eine lokale SQLite-Datenbank verwendet.

### 4. Drag-and-Drop Rack-Planer
* **Konzept:** Geräte-Positionierung vereinfachen.
* **Feature:** Server und PDUs können per Drag-and-Drop im Rack verschoben werden. Die U-Höhe und Seiten-Validierung findet interaktiv im Frontend statt.
