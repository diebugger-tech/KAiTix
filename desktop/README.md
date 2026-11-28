# KAiTix als Desktop-App (Linux, Prototyp)

KAiTix läuft als eigenes Fenster auf dem eigenen Rechner, ohne Container und ohne
Server im Netz. Muster: die GoTV-Installation aus dem Git-Checkout.

- Ein lokaler Server nur auf `127.0.0.1:8790` liefert API und Oberfläche aus.
- Das Fenster ist ein Chromium-App-Fenster (Chromium, Chrome, Edge oder Brave; nativ,
  Flatpak oder Snap) mit eigenem Profil.
- Daten: `~/.local/share/kaitix/kaitix.db`, getrennt vom Entwicklungsstand in `data/`.
- **Nach Updates suchen** in der Seitenleiste: `git fetch`, zeigt die neuen Commits;
  **Jetzt aktualisieren** macht `git pull --ff-only`, baut neu und startet KAiTix neu.

## Installieren

Voraussetzungen: `git`, `python3`, `npm` (Node 20+), `curl`, ein Chromium-Browser.

```bash
cd ~/Projekte/aktiv/KAiTix
git switch feature/desktop        # solange der Prototyp nicht in main ist
sh desktop/install.sh
```

Die Installation:

1. legt `.venv` an, falls nicht vorhanden, und installiert `requirements.txt`. Das
   passiert nur, wenn sich die Datei geändert hat.
2. baut die Oberfläche (`npm ci` nur bei geänderter `package-lock.json`).
3. legt den Starter `~/.local/bin/launch-kaitix`, das Icon und den Menüeintrag „KAiTix“
   an.

Kein sudo, keine Systemdateien. Mit `KAITIX_PYTHON=/pfad/zu/python sh desktop/install.sh`
nutzt die App ein vorhandenes Python mit allen Paketen und lässt `.venv` in Ruhe.

## Starten und beenden

- Starten: im App-Menü **KAiTix**, oder `launch-kaitix`.
- Das Fenster zu schließen beendet den Server nicht. `launch-kaitix stop` beendet ihn,
  die Daten bleiben.
- Beim ersten Start mit leerer Datenbank lädt KAiTix Demo-Daten.
  `KAITIX_DEMO_DATEN=0 launch-kaitix` startet stattdessen leer.
- Log: `~/.local/share/kaitix/server.log`

## Updates

Der Update-Knopf aktualisiert den Branch, der im Checkout ausgecheckt ist, von dessen
Upstream (`git pull --ff-only`).

- Es wird nur auf Knopfdruck geprüft, nie im Hintergrund.
- Kein Update, wenn der Checkout eigene Änderungen oder eigene Commits hat. Der Knopf
  sagt dann, warum.
- Nach dem Neubau startet der Server neu. Stehen Migrationen aus, kopiert der Launcher
  die Datenbank vorher nach `~/.local/share/kaitix/sicherungen/`. Behalten werden die
  letzten 10 Kopien. Danach läuft `alembic upgrade head`.

Ablauf zwischen zwei Rechnern: auf Rechner A ändern, committen und pushen. Auf Rechner B
**Nach Updates suchen**, dann **Jetzt aktualisieren**.

## Vorhandene Daten übernehmen

Vor dem ersten Start die bisherige Datenbank kopieren:

```bash
mkdir -p ~/.local/share/kaitix
cp data/kaitix.db ~/.local/share/kaitix/kaitix.db
```

Beim Start laufen ausstehende Migrationen, vorher wird gesichert.

## Sicherheit

- Der Server lauscht nur auf `127.0.0.1` und nimmt nur die Host-Namen `127.0.0.1` und
  `localhost` an. Das schützt gegen DNS-Rebinding.
- Die Update-Aktionen verlangen eine Anfrage von 127.0.0.1, den Header `X-KAiTix-Update`
  und, falls gesendet, eine lokale Origin. Sie führen nur feste Befehle aus. Aus der
  Anfrage wird nichts übernommen.
- `launch-kaitix` öffnet keinen Server, dessen Prozess einem anderen Nutzer gehört.

## Umgebung

| Variable | Standard | Zweck |
|---|---|---|
| `KAITIX_DESKTOP_PORT` | `8790` | Port des lokalen Servers |
| `KAITIX_DATA_DIR` | `~/.local/share/kaitix` | Datenbank, Sicherungen, Log, Browser-Profil |
| `KAITIX_BROWSER` | erkannt | Befehl für das App-Fenster |
| `KAITIX_PYTHON` | `.venv/bin/python` | Python mit allen Paketen |
| `KAITIX_DEMO_DATEN` | `1` | `0`: neue Datenbank ohne Demo-Daten |

## Deinstallieren

`sh desktop/uninstall.sh` entfernt Starter, Icon und Menüeintrag. Daten und Checkout
bleiben.

## Grenzen des Prototyps

- Nur Linux. Für Windows und macOS ist der nächste Schritt eine Tauri-App mit
  eingebautem Python (PyInstaller) und Installern aus GitHub Actions, wie bei GoTV.
- Updates kommen aus dem Git-Checkout. Es gibt keine fertigen Pakete (AppImage, deb).
- Je Rechner eine eigene Datenbank. Ein gemeinsamer Stand fürs Team bleibt die
  Container-Variante.
