# uninstall.sh - Entfernt Starter, Icon und Menüeintrag der KAiTix Desktop-App.
# Kein Shebang und kein Ausrufezeichen (Regel: zsh History Expansion).
# Daten (~/.local/share/kaitix) und der Checkout bleiben erhalten.

set -u

HOME_DIR="${KAITIX_INSTALL_HOME:-$HOME}"

if [ -x "$HOME_DIR/.local/bin/launch-kaitix" ]; then
  sh "$HOME_DIR/.local/bin/launch-kaitix" stop
fi

rm -f "$HOME_DIR/.local/bin/launch-kaitix" \
      "$HOME_DIR/.local/share/applications/kaitix.desktop" \
      "$HOME_DIR/.local/share/icons/hicolor/scalable/apps/kaitix.svg"
rm -rf "$HOME_DIR/.config/kaitix"

if command -v update-desktop-database > /dev/null 2>&1; then
  update-desktop-database "$HOME_DIR/.local/share/applications" 2> /dev/null
fi

echo "KAiTix Desktop entfernt."
echo "Daten bleiben: ${XDG_DATA_HOME:-$HOME_DIR/.local/share}/kaitix (Datenbank, Sicherungen, Log)."
