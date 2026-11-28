"""Desktop-App: Version und „Nach Updates suchen“.

Aktiv nur, wenn der Launcher (desktop/kaitix_desktop.py) KAITIX_DESKTOP_REPO setzt;
sonst antworten alle Endpunkte 404 (Container, Entwicklung). Die Update-Aktionen
nehmen nur Anfragen von 127.0.0.1 an, mit dem Header X-KAiTix-Update und, falls
vorhanden, einer lokalen Origin.
"""

import asyncio
import ipaddress
import os
import signal
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.domains.desktop.updater import Updater, UpdateFehler

router = APIRouter()

REPO_ENV = "KAITIX_DESKTOP_REPO"
NEUSTART_ENV = "KAITIX_DESKTOP_NEUSTART"
UPDATE_HEADER = "x-kaitix-update"
NEUSTART_VERZOEGERUNG = 1.5  # Sekunden, damit die Antwort noch ankommt


class UpdateStandOut(BaseModel):
    branch: str | None
    upstream: str | None
    lokal: str
    remote: str | None
    hinter: int
    vor: int
    lokale_aenderungen: bool
    neu: list[str]
    sperrgrund: str | None


class UpdateErgebnis(BaseModel):
    log: list[str]
    neustart: bool


def _repo() -> Path:
    pfad = os.environ.get(REPO_ENV)
    if not pfad:
        raise HTTPException(status_code=404, detail="Nur in der Desktop-App verfügbar.")
    return Path(pfad)


def _nur_lokal(request: Request) -> None:
    """Nur der eigene Rechner, nur absichtlich (Header), keine fremde Webseite (Origin)."""
    host = request.client.host if request.client else ""
    try:
        lokal = ipaddress.ip_address(host).is_loopback
    except ValueError:
        lokal = host == "localhost"
    if not lokal:
        raise HTTPException(status_code=403, detail="Updates nur vom eigenen Rechner.")
    if request.headers.get(UPDATE_HEADER) != "1":
        raise HTTPException(status_code=403, detail="Header X-KAiTix-Update fehlt.")
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).hostname not in ("127.0.0.1", "localhost"):
        raise HTTPException(status_code=403, detail="Fremde Origin.")


def neustart_anfordern() -> bool:
    """Markiert den Neustart für den Launcher und beendet den Server kurz darauf."""
    flagge = os.environ.get(NEUSTART_ENV)
    if not flagge:
        return False
    Path(flagge).write_text("update\n", encoding="utf-8")
    threading.Timer(
        NEUSTART_VERZOEGERUNG, lambda: os.kill(os.getpid(), signal.SIGTERM)
    ).start()
    return True


@router.get("/info")
async def info() -> dict[str, Any]:
    """Version der Desktop-Installation (Branch, Commit, Datum)."""
    repo = _repo()
    try:
        version = await asyncio.to_thread(Updater(repo).version)
    except UpdateFehler:
        version = {"branch": None, "commit": None, "datum": None}
    return {"desktop": True, **version}


@router.post("/update/pruefen", response_model=UpdateStandOut)
async def update_pruefen(request: Request) -> dict[str, Any]:
    """git fetch und Vergleich mit dem Upstream. Ändert nichts am Checkout."""
    repo = _repo()
    _nur_lokal(request)
    try:
        stand = await asyncio.to_thread(Updater(repo).pruefen)
    except UpdateFehler as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {**stand.__dict__, "sperrgrund": stand.sperrgrund}


@router.post("/update/ausfuehren", response_model=UpdateErgebnis)
async def update_ausfuehren(request: Request) -> dict[str, Any]:
    """git pull --ff-only, Neubau, danach Neustart durch den Launcher."""
    repo = _repo()
    _nur_lokal(request)
    try:
        log = await asyncio.to_thread(Updater(repo).ausfuehren)
    except UpdateFehler as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"log": log, "neustart": neustart_anfordern()}
