"""„Nach Updates suchen“ für die Desktop-Installation (Muster: GoTV script_update.py).

Die Desktop-App läuft aus einem Git-Checkout (desktop/install.sh). Es gibt genau zwei
feste Aktionen; nichts davon kommt aus der Anfrage (kein Branch, kein Pfad, kein Argument):

- pruefen:    git fetch, dann wie viele Commits der Checkout hinter seinem Upstream
              liegt, welche das sind und ob es eigene Änderungen gibt.
- ausfuehren: git pull --ff-only, dann `sh desktop/install.sh --update` (Oberfläche
              bauen, Abhängigkeiten nachziehen). Den Neustart und die Migrationen
              übernimmt danach der Launcher (desktop/kaitix_desktop.py).

Netz wird nur auf Knopfdruck benutzt (git fetch/pull gegen das eigene Repository).
"""

import os
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

FETCH_TIMEOUT = 90
PULL_TIMEOUT = 180
INSTALL_TIMEOUT = 20 * 60
LOG_ZEILEN = 60
INSTALL_BEFEHL = ("sh", "desktop/install.sh", "--update")


class UpdateFehler(Exception):
    """Fachlicher Fehler, der dem Nutzer als Satz gezeigt wird."""


@dataclass(frozen=True)
class UpdateStand:
    branch: str | None
    upstream: str | None
    lokal: str
    remote: str | None
    hinter: int
    vor: int
    lokale_aenderungen: bool
    neu: list[str] = field(default_factory=list)

    @property
    def sperrgrund(self) -> str | None:
        """Warum „Aktualisieren“ gerade nicht geht. None = möglich."""
        if self.upstream is None:
            return "Der Branch hat keinen Upstream; git pull weiß nicht, woher."
        if self.lokale_aenderungen:
            return (
                "Im Checkout gibt es eigene Änderungen. Erst committen oder verwerfen."
            )
        if self.vor:
            return (
                f"Der Checkout hat {self.vor} eigene(n) Commit(s), die nicht auf dem "
                "Server sind. Ein Update ohne Zusammenführen ist nicht möglich."
            )
        if not self.hinter:
            return "KAiTix ist aktuell."
        return None


def _werkzeug_pfad() -> str:
    """PATH für git/npm: ein Desktop-Starter kennt oft das Nix-Profil nicht."""
    home = os.path.expanduser("~")
    extra = [
        os.path.join(home, ".nix-profile", "bin"),
        "/nix/var/nix/profiles/default/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
    ]
    teile = (os.environ.get("PATH") or "").split(os.pathsep)
    teile += [eintrag for eintrag in extra if eintrag not in teile]
    return os.pathsep.join(t for t in teile if t)


class Updater:
    # Ein Update zur Zeit, auch über mehrere Anfragen hinweg.
    _laeuft = threading.Lock()

    def __init__(self, repo: Path, install_befehl: Sequence[str] = INSTALL_BEFEHL):
        self.repo = repo
        self.install_befehl = tuple(install_befehl)

    # --- Hilfen -------------------------------------------------------------------
    def _env(self) -> dict[str, str]:
        return {**os.environ, "PATH": _werkzeug_pfad(), "GIT_TERMINAL_PROMPT": "0"}

    def _run(
        self, befehl: Sequence[str], timeout: float
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                list(befehl),
                cwd=self.repo,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._env(),
            )
        except FileNotFoundError as exc:
            raise UpdateFehler(f"Programm nicht gefunden: {befehl[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise UpdateFehler(
                f"Zeitüberschreitung nach {int(timeout)} s: {' '.join(befehl)}"
            ) from exc

    def _git(self, *args: str, timeout: float = 30) -> str:
        ergebnis = self._run(["git", *args], timeout)
        if ergebnis.returncode != 0:
            raise UpdateFehler(
                f"git {args[0]} fehlgeschlagen: "
                f"{(ergebnis.stderr or ergebnis.stdout).strip()[:300]}"
            )
        return ergebnis.stdout.strip()

    def _git_oder_none(self, *args: str) -> str | None:
        ergebnis = self._run(["git", *args], 30)
        return ergebnis.stdout.strip() if ergebnis.returncode == 0 else None

    # --- Lesen ----------------------------------------------------------------------
    def version(self) -> dict[str, str | None]:
        return {
            "branch": self._git_oder_none("rev-parse", "--abbrev-ref", "HEAD"),
            "commit": self._git_oder_none("rev-parse", "--short", "HEAD"),
            "datum": self._git_oder_none("log", "-1", "--format=%cs"),
        }

    def stand(self) -> UpdateStand:
        """Stand gegenüber dem zuletzt geholten Upstream, ohne Netz."""
        branch = self._git_oder_none("rev-parse", "--abbrev-ref", "HEAD")
        upstream = self._git_oder_none(
            "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"
        )
        lokal = self._git("rev-parse", "--short", "HEAD")
        aenderungen = bool(self._git("status", "--porcelain", "--untracked-files=no"))
        if upstream is None:
            return UpdateStand(branch, None, lokal, None, 0, 0, aenderungen)
        remote = self._git("rev-parse", "--short", "@{u}")
        vor, hinter = (
            int(zahl)
            for zahl in self._git(
                "rev-list", "--left-right", "--count", "HEAD...@{u}"
            ).split()
        )
        neu = (
            self._git(
                "log", "--format=%h %s", f"-{LOG_ZEILEN}", "HEAD..@{u}"
            ).splitlines()
            if hinter
            else []
        )
        return UpdateStand(
            branch, upstream, lokal, remote, hinter, vor, aenderungen, neu
        )

    # --- Aktionen ---------------------------------------------------------------------
    def pruefen(self) -> UpdateStand:
        self._git("fetch", "--quiet", timeout=FETCH_TIMEOUT)
        return self.stand()

    def ausfuehren(self) -> list[str]:
        """Pull und Neubau. Gibt das Protokoll zurück; wirft UpdateFehler."""
        if not self._laeuft.acquire(blocking=False):
            raise UpdateFehler("Ein Update läuft bereits.")
        try:
            stand = self.pruefen()
            if stand.sperrgrund:
                raise UpdateFehler(stand.sperrgrund)
            log = [f"Update {stand.lokal} → {stand.remote} ({stand.hinter} Commit(s))"]
            log.append(self._git("pull", "--ff-only", "--quiet", timeout=PULL_TIMEOUT))
            ergebnis = self._run(self.install_befehl, INSTALL_TIMEOUT)
            log += (ergebnis.stdout + ergebnis.stderr).splitlines()[-LOG_ZEILEN:]
            if ergebnis.returncode != 0:
                raise UpdateFehler(
                    "Code ist aktualisiert, aber der Neubau ist fehlgeschlagen:\n"
                    + "\n".join(log[-15:])
                )
            return [zeile for zeile in log if zeile]
        finally:
            self._laeuft.release()
