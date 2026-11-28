"""„Nach Updates suchen“ der Desktop-App: Updater gegen echte Wegwerf-Git-Repos, Router-Schutz.

Aufbau je Test: ein Bare-Repo als „Server“, ein Klon als Installation, ein zweiter Klon,
aus dem neue Commits gepusht werden. Kein Netz, kein Install-Skript (ersetzt durch `true`).
"""

import subprocess
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.domains.desktop import router as desktop_router
from app.domains.desktop.updater import Updater, UpdateFehler

API = "/api/v1/desktop"
UPDATE = {"X-KAiTix-Update": "1"}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],  # fmt: skip
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _commit(repo: Path, datei: str, inhalt: str, nachricht: str) -> None:
    (repo / datei).write_text(inhalt, encoding="utf-8")
    _git(repo, "add", datei)
    _git(repo, "commit", "-q", "-m", nachricht)


@pytest.fixture
def repos(tmp_path: Path) -> tuple[Path, Path]:
    """(installation, entwicklung) mit gemeinsamem Bare-Repo als Upstream."""
    server = tmp_path / "server.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(server)], check=True
    )
    entwicklung = tmp_path / "entwicklung"
    subprocess.run(["git", "clone", "-q", str(server), str(entwicklung)], check=True)
    _git(entwicklung, "checkout", "-q", "-b", "main")
    _commit(entwicklung, "README.md", "v1\n", "erster Stand")
    _git(entwicklung, "push", "-q", "-u", "origin", "main")
    installation = tmp_path / "installation"
    subprocess.run(["git", "clone", "-q", str(server), str(installation)], check=True)
    return installation, entwicklung


def _updater(repo: Path) -> Updater:
    return Updater(repo, install_befehl=("true",))


# === Updater ==================================================================
def test_aktuell_ohne_neue_commits(repos):
    installation, _ = repos

    stand = _updater(installation).pruefen()

    assert stand.hinter == 0
    assert stand.upstream == "origin/main"
    assert stand.sperrgrund == "KAiTix ist aktuell."


def test_neue_commits_werden_gefunden_und_eingespielt(repos):
    installation, entwicklung = repos
    _commit(entwicklung, "README.md", "v2\n", "zweiter Stand")
    _commit(entwicklung, "neu.txt", "x\n", "dritter Stand")
    _git(entwicklung, "push", "-q")
    updater = _updater(installation)

    stand = updater.pruefen()
    assert stand.hinter == 2
    assert [zeile.split(" ", 1)[1] for zeile in stand.neu] == [
        "dritter Stand",
        "zweiter Stand",
    ]
    assert stand.sperrgrund is None

    log = updater.ausfuehren()

    assert log[0].startswith("Update ")
    assert (installation / "neu.txt").exists()
    assert updater.pruefen().hinter == 0


def test_eigene_aenderungen_verhindern_das_update(repos):
    installation, entwicklung = repos
    _commit(entwicklung, "README.md", "v2\n", "zweiter Stand")
    _git(entwicklung, "push", "-q")
    (installation / "README.md").write_text("lokal geändert\n", encoding="utf-8")
    updater = _updater(installation)

    assert updater.pruefen().lokale_aenderungen
    with pytest.raises(UpdateFehler, match="eigene Änderungen"):
        updater.ausfuehren()
    assert (installation / "README.md").read_text(
        encoding="utf-8"
    ) == "lokal geändert\n"


def test_eigene_commits_verhindern_das_update(repos):
    installation, entwicklung = repos
    _commit(entwicklung, "README.md", "v2\n", "zweiter Stand")
    _git(entwicklung, "push", "-q")
    _commit(installation, "lokal.txt", "x\n", "lokaler Commit")
    updater = _updater(installation)

    stand = updater.pruefen()

    assert (stand.vor, stand.hinter) == (1, 1)
    with pytest.raises(UpdateFehler, match="eigene"):
        updater.ausfuehren()


def test_fehlgeschlagener_neubau_wird_gemeldet(repos):
    installation, entwicklung = repos
    _commit(entwicklung, "README.md", "v2\n", "zweiter Stand")
    _git(entwicklung, "push", "-q")

    with pytest.raises(UpdateFehler, match="Neubau ist fehlgeschlagen"):
        Updater(installation, install_befehl=("false",)).ausfuehren()


# === Router ===================================================================
async def test_ohne_desktop_modus_404(client: AsyncClient, monkeypatch):
    monkeypatch.delenv(desktop_router.REPO_ENV, raising=False)

    assert (await client.get(f"{API}/info")).status_code == 404
    antwort = await client.post(f"{API}/update/pruefen", headers=UPDATE)
    assert antwort.status_code == 404


async def test_update_braucht_header_und_lokale_origin(
    client: AsyncClient, monkeypatch, repos
):
    installation, _ = repos
    monkeypatch.setenv(desktop_router.REPO_ENV, str(installation))

    ohne_header = await client.post(f"{API}/update/pruefen")
    fremde_origin = await client.post(
        f"{API}/update/pruefen", headers={**UPDATE, "Origin": "https://example.com"}
    )
    erlaubt = await client.post(
        f"{API}/update/pruefen",
        headers={**UPDATE, "Origin": "http://127.0.0.1:8790"},
    )

    assert ohne_header.status_code == 403
    assert fremde_origin.status_code == 403
    assert erlaubt.status_code == 200, erlaubt.text
    assert erlaubt.json()["sperrgrund"] == "KAiTix ist aktuell."


async def test_info_und_update_ueber_die_api(client: AsyncClient, monkeypatch, repos):
    installation, entwicklung = repos
    _commit(entwicklung, "README.md", "v2\n", "zweiter Stand")
    _git(entwicklung, "push", "-q")
    monkeypatch.setenv(desktop_router.REPO_ENV, str(installation))
    monkeypatch.setattr(desktop_router, "Updater", _updater)
    monkeypatch.setattr(desktop_router, "neustart_anfordern", lambda: True)

    info = (await client.get(f"{API}/info")).json()
    stand = (await client.post(f"{API}/update/pruefen", headers=UPDATE)).json()
    ergebnis = await client.post(f"{API}/update/ausfuehren", headers=UPDATE)
    nochmal = await client.post(f"{API}/update/ausfuehren", headers=UPDATE)

    assert info["desktop"] is True
    assert info["branch"] == "main"
    assert stand["hinter"] == 1
    assert ergebnis.status_code == 200, ergebnis.text
    assert ergebnis.json()["neustart"] is True
    assert nochmal.status_code == 409
    assert nochmal.json()["detail"] == "KAiTix ist aktuell."


def test_desktop_app_nimmt_nur_lokale_hosts_an(monkeypatch, tmp_path):
    """DNS-Rebinding: Host evil.example wird abgelehnt, 127.0.0.1 angenommen."""
    import importlib

    from fastapi.testclient import TestClient

    import app.main

    monkeypatch.setenv(desktop_router.REPO_ENV, str(tmp_path))
    try:
        desktop_app = importlib.reload(app.main).app
        client = TestClient(desktop_app)
        fremd = client.get("/api/v1/kabeltypen/", headers={"Host": "evil.example:8790"})
        lokal = client.get("/api/v1/desktop/info", headers={"Host": "127.0.0.1:8790"})
        assert fremd.status_code == 400
        assert lokal.status_code == 200
        assert lokal.json()["commit"] is None  # kein Git-Checkout
    finally:
        monkeypatch.delenv(desktop_router.REPO_ENV)
        importlib.reload(app.main)
