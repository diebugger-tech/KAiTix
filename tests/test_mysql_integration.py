"""
MySQL-Integrationstests für KAiTix

Diese Tests validieren die DB-Schicht gegen eine echte MySQL 8-Instanz.
Sie werden NICHT im Standard-Testlauf ausgeführt (siehe @pytest.mark.integration).

Ausführung:
    pytest -m integration tests/test_mysql_integration.py

Voraussetzungen:
    - Docker oder Podman muss laufen (für Testcontainers)
    - testcontainers[mysql] muss installiert sein

Hinweis:
    Die Standard-Test-Suite (38 Tests) läuft gegen SQLite für Geschwindigkeit.
    Diese Integrationstests ergänzen sie um MySQL-spezifische Validierung.
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import Base, get_db
from testcontainers.mysql import MySqlContainer

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(scope="module")
async def mysql_engine():
    """
    Startet einen MySQL 8-Container via Testcontainers.
    Erzeugt alle Tabellen via Alembic/SQLAlchemy.
    """
    with MySqlContainer("mysql:8") as mysql:
        db_url = mysql.get_connection_url()
        # Testcontainers liefert sync-URL; wir bauen async-URL
        async_url = db_url.replace("pymysql", "aiomysql")
        engine = create_async_engine(async_url)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        await engine.dispose()


@pytest_asyncio.fixture
async def mysql_db(mysql_engine) -> AsyncGenerator[AsyncSession, None]:
    """Bietet eine frische Session pro Test mit Rollback."""
    async with mysql_engine.connect() as connection:
        transaction = await connection.begin()
        TestingSessionLocal = async_sessionmaker(
            bind=connection, expire_on_commit=False
        )
        async_session = TestingSessionLocal()
        yield async_session
        await async_session.close()
        await transaction.rollback()


@pytest_asyncio.fixture
async def mysql_client(mysql_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP-Client mit überschriebener DB-Dependency (MySQL)."""

    async def override_get_db():
        yield mysql_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


class TestMySQLConnection:
    """Validiert grundlegende MySQL-Konnektivität."""

    @pytest.mark.asyncio
    async def test_mysql_ping(self, mysql_engine):
        async with mysql_engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_tables_created(self, mysql_engine):
        async with mysql_engine.connect() as conn:
            result = await conn.execute("SHOW TABLES LIKE 'racks'")
            assert result.fetchone() is not None


class TestMySQLRackCRUD:
    """Validiert Rack-CRUD gegen MySQL (inkl. Foreign Keys, Cascading)."""

    @pytest.mark.asyncio
    async def test_create_and_read_rack(self, mysql_client: AsyncClient):
        payload = {
            "name": "MySQL-Rack-01",
            "standort": "RZ Test",
            "hoehe_u": 42,
        }
        resp = await mysql_client.post("/api/v1/racks/", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "MySQL-Rack-01"

        rack_id = data["id"]
        resp = await mysql_client.get(f"/api/v1/racks/{rack_id}")
        assert resp.status_code == 200
        assert resp.json()["standort"] == "RZ Test"

    @pytest.mark.asyncio
    async def test_rack_delete_cascade_mysql(
        self, mysql_client: AsyncClient, mysql_db: AsyncSession
    ):
        """
        MySQL: CASCADE-Deletes müssen konsistent funktionieren.
        (Unterscheidet sich von SQLite bei FOREIGN_KEY-Checks.)
        """
        # Rack anlegen
        rack_resp = await mysql_client.post(
            "/api/v1/racks/",
            json={
                "name": "Cascade-Rack",
                "standort": "Test",
                "hoehe_u": 42,
            },
        )
        rack_id = rack_resp.json()["id"]

        # Gerät im Rack anlegen
        device_resp = await mysql_client.post(
            "/api/v1/devices/",
            json={
                "hostname": "srv-cascade",
                "typ": "server",
                "hoehe_u_start": 1,
                "u_hoehe": 1,
                "rack_id": rack_id,
            },
        )
        assert device_resp.status_code == 200

        # Rack löschen → Gerät sollte mitgelöscht werden (CASCADE)
        del_resp = await mysql_client.delete(f"/api/v1/racks/{rack_id}")
        assert del_resp.status_code == 200

        # Gerät sollte nicht mehr existieren
        from app.domains.hardware.models import Device

        result = await mysql_db.execute(
            __import__("sqlalchemy", fromlist=["select"])
            .select(Device)
            .where(Device.hostname == "srv-cascade")
        )
        assert result.scalar_one_or_none() is None
