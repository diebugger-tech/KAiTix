"""DB-Bootstrap für den Container-Start.

Hintergrund: Das Projekt besitzt KEINE Initial-Create-Migration. Die
Alembic-Kette beginnt mit `bb2406ada639`, die bereits bestehende Tabellen
voraussetzt (das Schema wurde historisch via `Base.metadata.create_all`
gebootstrappt). Ein nacktes `alembic upgrade head` scheitert daher auf einer
leeren DB ("Table 'cable_strands' doesn't exist").

Dieses Skript macht den Start robust:
- **Frische DB** (kein `alembic_version`, kein Schema): Schema direkt aus den
  Modellen anlegen (`create_all`) und auf `head` stampen.
- **Bestehende DB**: normale Migration auf `head`.
"""

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.database import Base, engine
import app.models  # noqa: F401  registriert ALLE Tabellen in Base.metadata

ALEMBIC_INI = str(Path(__file__).resolve().parents[1] / "alembic.ini")


def _alembic_cfg() -> Config:
    return Config(ALEMBIC_INI)


async def _probe() -> tuple[bool, bool]:
    """(alembic_version vorhanden?, Kern-Schema vorhanden?)"""
    async with engine.connect() as conn:

        def _check(sync_conn):
            insp = inspect(sync_conn)
            return insp.has_table("alembic_version"), insp.has_table("racks")

        return await conn.run_sync(_check)


async def main() -> None:
    has_alembic, has_core = await _probe()

    if not has_alembic and not has_core:
        print(">>> Frische DB erkannt — erstelle Schema aus Modellen (create_all)...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        command.stamp(_alembic_cfg(), "head")
        print(">>> Schema erstellt und auf 'head' gestampt.")
    else:
        print(">>> Bestehende DB — wende Migrationen auf 'head' an...")
        command.upgrade(_alembic_cfg(), "head")
        print(">>> Migrationen auf 'head' angewendet.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
