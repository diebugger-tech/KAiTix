# install.sh - Installiert die KAiTix Desktop-App für den aktuellen Nutzer (Linux).
# Kein Shebang und kein Ausrufezeichen (Regel: zsh History Expansion).
#
#   sh desktop/install.sh            Abhängigkeiten, Oberfläche, Starter und Menüeintrag
#   sh desktop/install.sh --update   nur Abhängigkeiten und Oberfläche (vom Update-Knopf)
#
# Kein sudo, keine Systemdateien. Umgebung: KAITIX_PYTHON (vorhandenes Python mit allen
# Paketen statt .venv), KAITIX_INSTALL_HOME (Zielordner statt $HOME, für Tests).

set -u

HOME_DIR="${KAITIX_INSTALL_HOME:-$HOME}"
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
NUR_UPDATE=0
if [ "${1:-}" = "--update" ]; then
  NUR_UPDATE=1
fi

echo "KAiTix Desktop-Installation (Checkout: $ROOT_DIR)"

for werkzeug in git python3 npm curl; do
  if command -v "$werkzeug" > /dev/null 2>&1; then
    :
  else
    echo "$werkzeug fehlt. Installation abgebrochen."
    exit 1
  fi
done

cd "$ROOT_DIR" || exit 1

echo "1/3 Python-Umgebung..."
if [ -n "${KAITIX_PYTHON:-}" ]; then
  echo "    vorhandenes Python: $KAITIX_PYTHON (Pakete werden nicht angefasst)"
else
  if [ -x .venv/bin/python ]; then
    :
  else
    python3 -m venv .venv || exit 1
    rm -f .venv/.kaitix-requirements
  fi
  # Pakete nur nachziehen, wenn requirements.txt neuer ist als die letzte Installation.
  if [ -f .venv/.kaitix-requirements ] && [ .venv/.kaitix-requirements -nt requirements.txt ]; then
    echo "    Pakete aktuell"
  else
    .venv/bin/python -m pip install --quiet --upgrade pip || exit 1
    .venv/bin/python -m pip install --quiet -r requirements.txt || exit 1
    touch .venv/.kaitix-requirements
  fi
fi

echo "2/3 Oberfläche bauen..."
if [ -f frontend/node_modules/.package-lock.json ] && [ frontend/node_modules/.package-lock.json -nt frontend/package-lock.json ]; then
  :
else
  (cd frontend && npm ci --no-audit --no-fund) || exit 1
fi
(cd frontend && npm run build) || exit 1

if [ "$NUR_UPDATE" = "1" ]; then
  echo "3/3 Fertig (Update). Der Server startet neu, ausstehende Migrationen laufen dabei"
  echo "    mit vorheriger Sicherung der Datenbank."
  exit 0
fi

echo "3/3 Starter, Icon und Menüeintrag..."
mkdir -p "$HOME_DIR/.local/bin" \
         "$HOME_DIR/.local/share/applications" \
         "$HOME_DIR/.local/share/icons/hicolor/scalable/apps" \
         "$HOME_DIR/.config/kaitix"

echo "$ROOT_DIR" > "$HOME_DIR/.config/kaitix/root-path"
if [ -n "${KAITIX_PYTHON:-}" ]; then
  echo "$KAITIX_PYTHON" > "$HOME_DIR/.config/kaitix/python"
else
  rm -f "$HOME_DIR/.config/kaitix/python"
fi

# Kleiner Starter: ruft immer den Launcher aus dem Checkout auf. So kommen Änderungen
# am Launcher mit jedem Update an, ohne neu zu installieren.
{
  echo "# launch-kaitix - Starter der KAiTix Desktop-App (erzeugt von desktop/install.sh)"
  echo "if [ -r \"\$HOME/.config/kaitix/python\" ]; then"
  echo "  KAITIX_PYTHON=\"\${KAITIX_PYTHON:-\$(cat \"\$HOME/.config/kaitix/python\")}\""
  echo "  export KAITIX_PYTHON"
  echo "fi"
  echo "exec sh \"$ROOT_DIR/desktop/launch-kaitix\" \"\$@\""
} > "$HOME_DIR/.local/bin/launch-kaitix"
chmod +x "$HOME_DIR/.local/bin/launch-kaitix"

cp "$ROOT_DIR/desktop/icons/kaitix.svg" \
   "$HOME_DIR/.local/share/icons/hicolor/scalable/apps/kaitix.svg"

sed "s|@INSTALL_HOME@|$HOME_DIR|" \
  "$ROOT_DIR/desktop/kaitix.desktop" \
  > "$HOME_DIR/.local/share/applications/kaitix.desktop"
chmod +x "$HOME_DIR/.local/share/applications/kaitix.desktop"

if command -v update-desktop-database > /dev/null 2>&1; then
  update-desktop-database "$HOME_DIR/.local/share/applications" 2> /dev/null
fi
if command -v gtk-update-icon-cache > /dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$HOME_DIR/.local/share/icons/hicolor" 2> /dev/null
fi

echo "Fertig."
echo "  Im App-Menü:  KAiTix"
echo "  Starter:      $HOME_DIR/.local/bin/launch-kaitix   (beenden: launch-kaitix stop)"
echo "  Daten:        ~/.local/share/kaitix/kaitix.db"
echo "  Server-Log:   ~/.local/share/kaitix/server.log"
echo "Deinstallation: sh $ROOT_DIR/desktop/uninstall.sh"
