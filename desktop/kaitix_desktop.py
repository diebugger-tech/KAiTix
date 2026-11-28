"""kaitix_desktop.py - Server der KAiTix-Desktop-App (Linux, Git-Checkout).

Bereitet die Datenbank vor, startet KAiTix (API + gebaute Oberfläche) nur auf
127.0.0.1 und startet den Server nach einem Update neu:

1. Datenbank in ~/.local/share/kaitix/kaitix.db (KAITIX_DATA_DIR überschreibt).
2. Stehen Migrationen aus, wird die Datenbank vorher nach .../sicherungen/ kopiert.
3. scripts/db_init.py: neue Datenbank aus den Modellen, sonst alembic upgrade head.
4. Neue Datenbank: Demo-Daten laden (KAITIX_DEMO_DATEN=0 schaltet das ab).
5. uvicorn starten. Endet er nach „Aktualisieren“ (Markierungsdatei „neustart“),
   beginnt der Ablauf bei 2 von vorn, sonst endet auch dieses Programm.

Start über desktop/launch-kaitix. Aufruf direkt:
    .venv/bin/python desktop/kaitix_desktop.py [--port N] [--daten DIR]
"""

import argparse
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STANDARD_PORT = 8790
SICHERUNGEN_BEHALTEN = 10


def standard_daten() -> Path:
    if os.environ.get("KAITIX_DATA_DIR"):
        return Path(os.environ["KAITIX_DATA_DIR"]).expanduser()
    basis = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(basis) / "kaitix"


def melde(text: str) -> None:
    print(f"[kaitix-desktop {time.strftime('%Y-%m-%d %H:%M:%S')}] {text}", flush=True)


def umgebung(daten: Path, port: int) -> dict[str, str]:
    db = daten / "kaitix.db"
    return {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{db}",
        "ALLOWED_ORIGINS": f"http://127.0.0.1:{port},http://localhost:{port}",
        "KAITIX_DESKTOP_REPO": str(REPO),
        "KAITIX_DESKTOP_NEUSTART": str(daten / "neustart"),
        "PYTHONPATH": str(REPO),
    }


# --- Datenbank ------------------------------------------------------------------------
def db_revision(db: Path) -> str | None:
    """Aktuelle Alembic-Revision der Datenbank; None = neu oder ohne Alembic."""
    if not db.exists():
        return None
    with sqlite3.connect(db) as verbindung:
        try:
            zeile = verbindung.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()
        except sqlite3.OperationalError:
            return None
    return zeile[0] if zeile else None


def code_revision() -> str | None:
    """Neueste Migration im Checkout (alembic head)."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(REPO / "alembic.ini"))
    config.set_main_option("script_location", str(REPO / "alembic"))
    return ScriptDirectory.from_config(config).get_current_head()


def sichern(db: Path, revision: str) -> Path:
    ordner = db.parent / "sicherungen"
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = ordner / f"kaitix-{time.strftime('%Y%m%d-%H%M%S')}-{revision}.db"
    # sqlite3-Backup statt Dateikopie: konsistent, auch mit offener WAL-Datei.
    with sqlite3.connect(db) as quelle, sqlite3.connect(ziel) as kopie:
        quelle.backup(kopie)
    alte = sorted(ordner.glob("kaitix-*.db"))[:-SICHERUNGEN_BEHALTEN]
    for datei in alte:
        datei.unlink()
    return ziel


def db_vorbereiten(daten: Path, env: dict[str, str]) -> None:
    db = daten / "kaitix.db"
    neu = not db.exists()
    vorher = db_revision(db)
    if vorher is not None and vorher != code_revision():
        melde(f"Migrationen ausstehend ({vorher}); Sicherung: {sichern(db, vorher)}")
    subprocess.run(
        [sys.executable, "scripts/db_init.py"], cwd=REPO, env=env, check=True
    )
    if neu and os.environ.get("KAITIX_DEMO_DATEN", "1") != "0":
        melde("Neue Datenbank: lade Demo-Daten")
        subprocess.run(
            [sys.executable, "scripts/seed_testdata.py", "--if-empty"],
            cwd=REPO,
            env=env,
            check=True,
        )


# --- Server ---------------------------------------------------------------------------
def server_starten(port: int, env: dict[str, str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(port),
        ],
        cwd=REPO,
        env=env,
    )  # fmt: skip


def main() -> int:
    parser = argparse.ArgumentParser(description="KAiTix Desktop-Server")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("KAITIX_DESKTOP_PORT", STANDARD_PORT)),
    )
    parser.add_argument("--daten", type=Path, default=standard_daten())
    args = parser.parse_args()

    daten: Path = args.daten
    daten.mkdir(parents=True, exist_ok=True)
    env = umgebung(daten, args.port)
    neustart = daten / "neustart"
    (daten / "kaitix.pid").write_text(str(os.getpid()), encoding="utf-8")

    server: subprocess.Popen[bytes] | None = None

    def beenden(signum: int, _frame: object) -> None:
        if server and server.poll() is None:
            server.terminate()
            server.wait(timeout=15)
        sys.exit(0)

    signal.signal(signal.SIGTERM, beenden)
    signal.signal(signal.SIGINT, beenden)

    try:
        while True:
            neustart.unlink(missing_ok=True)
            db_vorbereiten(daten, env)
            melde(f"Server startet auf http://127.0.0.1:{args.port} (Checkout {REPO})")
            server = server_starten(args.port, env)
            rueckgabe = server.wait()
            if neustart.exists():
                melde("Neustart nach Update")
                continue
            melde(f"Server beendet (Rückgabe {rueckgabe})")
            return rueckgabe
    finally:
        (daten / "kaitix.pid").unlink(missing_ok=True)


if __name__ == "__main__":
    if shutil.which("git") is None:
        melde("Hinweis: git fehlt, „Nach Updates suchen“ geht dann nicht.")
    sys.exit(main())
