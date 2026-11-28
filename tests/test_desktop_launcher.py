"""Launcher der Desktop-App: Alembic-Stand lesen und Datenbank vor Migrationen sichern."""

import importlib.util
import sqlite3
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[1] / "desktop" / "kaitix_desktop.py"
_spec = importlib.util.spec_from_file_location("kaitix_desktop", LAUNCHER)
assert _spec and _spec.loader
kaitix_desktop = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kaitix_desktop)


def _db(pfad: Path, revision: str | None) -> Path:
    with sqlite3.connect(pfad) as verbindung:
        verbindung.execute("CREATE TABLE racks (id INTEGER PRIMARY KEY, name TEXT)")
        verbindung.execute("INSERT INTO racks (name) VALUES ('R1')")
        if revision:
            verbindung.execute("CREATE TABLE alembic_version (version_num TEXT)")
            verbindung.execute("INSERT INTO alembic_version VALUES (?)", (revision,))
    return pfad


def test_db_revision(tmp_path: Path):
    assert kaitix_desktop.db_revision(tmp_path / "fehlt.db") is None
    assert kaitix_desktop.db_revision(_db(tmp_path / "ohne.db", None)) is None
    assert kaitix_desktop.db_revision(_db(tmp_path / "mit.db", "abc123")) == "abc123"


def test_code_revision_ist_der_alembic_head():
    assert kaitix_desktop.code_revision()


def test_sicherung_kopiert_daten_und_behaelt_die_neuesten(tmp_path: Path, monkeypatch):
    db = _db(tmp_path / "kaitix.db", "abc123")
    ordner = tmp_path / "sicherungen"
    ordner.mkdir()
    for nummer in range(12):
        (ordner / f"kaitix-20260101-0000{nummer:02d}-alt.db").write_text("x")

    ziel = kaitix_desktop.sichern(db, "abc123")

    with sqlite3.connect(ziel) as kopie:
        assert kopie.execute("SELECT name FROM racks").fetchall() == [("R1",)]
    assert ziel.name.endswith("-abc123.db")
    assert len(list(ordner.glob("kaitix-*.db"))) == kaitix_desktop.SICHERUNGEN_BEHALTEN
    assert ziel.exists()
