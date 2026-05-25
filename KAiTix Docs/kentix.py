"""
ServerFlow — Kentix Integration
Unterstützt: RACOnode, DoorMaster, MultiSensor
API: Kentix REST v2 (HTTP Basic Auth oder API-Key)

Install: pip install httpx schedule
"""

import os
import time
import json
import logging
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy.orm import Session

# Import aus cli.py (gemeinsame Models)
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from cli.cli import Device, engine  # type: ignore

logger = logging.getLogger("serverflow.kentix")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# ── Konstanten ────────────────────────────────────────────────
POLL_INTERVAL_SEC = int(os.getenv("KENTIX_POLL_INTERVAL", "60"))
KENTIX_TIMEOUT = 10  # Sekunden


# ══════════════════════════════════════════════════════════════
# KENTIX API CLIENT
# ══════════════════════════════════════════════════════════════
class KentixClient:
    """
    Generischer Kentix REST-Client.
    Unterstützt RACOnode-API v2.
    Dokumentation: Kentix RACOnode REST API Guide
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.auth = (username, password) if username else None

    def _headers(self) -> dict:
        h = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        return h

    def get(self, endpoint: str) -> dict:
        url = f"{self.base_url}{endpoint}"
        try:
            r = httpx.get(
                url,
                headers=self._headers(),
                auth=self.auth,
                timeout=KENTIX_TIMEOUT,
                verify=False,  # Selbst-signierte Zertifikate im LAN
            )
            r.raise_for_status()
            return r.json()
        except httpx.TimeoutException:
            logger.error(f"Timeout: {url}")
            return {}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code}: {url}")
            return {}
        except Exception as e:
            logger.error(f"Fehler bei GET {url}: {e}")
            return {}

    # ── Endpunkte ──────────────────────────────────────────────

    def get_status(self) -> dict:
        """Gerätestatus + Alarme."""
        return self.get("/api/v2/status")

    def get_sensors(self) -> dict:
        """Alle Sensor-Messwerte."""
        return self.get("/api/v2/sensors")

    def get_temperature(self) -> Optional[float]:
        data = self.get_sensors()
        try:
            return float(data["sensors"]["temperature"]["value"])
        except (KeyError, TypeError, ValueError):
            return None

    def get_humidity(self) -> Optional[float]:
        data = self.get_sensors()
        try:
            return float(data["sensors"]["humidity"]["value"])
        except (KeyError, TypeError, ValueError):
            return None

    def get_alarms(self) -> list:
        """Aktive Alarme als Liste."""
        data = self.get("/api/v2/alarms")
        return data.get("alarms", [])

    def is_alarm_active(self) -> bool:
        return len(self.get_alarms()) > 0

    def get_alarm_types(self) -> list[str]:
        alarms = self.get_alarms()
        return [a.get("type", "UNKNOWN") for a in alarms]


# ══════════════════════════════════════════════════════════════
# DB WRITE
# ══════════════════════════════════════════════════════════════


def write_reading(
    device_id: int,
    temp: Optional[float],
    humidity: Optional[float],
    alarm_aktiv: bool,
    alarm_typ: Optional[str],
    raw: dict,
):
    """Messwert in kentix_readings speichern."""
    with Session(engine) as s:
        s.execute(
            """
            INSERT INTO kentix_readings
                (device_id, gemessen_am, temperatur_c, luftfeuchte_pct, alarm_aktiv, alarm_typ, raw_json)
            VALUES
                (:device_id, :ts, :temp, :hum, :alarm, :atyp, :raw)
            """,
            {
                "device_id": device_id,
                "ts": datetime.now(),
                "temp": temp,
                "hum": humidity,
                "alarm": int(alarm_aktiv),
                "atyp": alarm_typ,
                "raw": json.dumps(raw),
            },
        )
        s.commit()


# ══════════════════════════════════════════════════════════════
# POLLER
# ══════════════════════════════════════════════════════════════


def get_kentix_devices() -> list[Device]:
    """Alle Kentix-Geräte mit API-URL aus DB laden."""
    with Session(engine) as s:
        return (
            s.query(Device)
            .filter(
                Device.typ.like("kentix_%"),
                Device.api_url.isnot(None),
            )
            .all()
        )


def poll_device(device: Device):
    """Ein Kentix-Gerät abfragen und Ergebnis speichern."""
    client = KentixClient(
        base_url=device.api_url,
        api_key=device.api_key,
    )

    temp = client.get_temperature()
    humidity = client.get_humidity()
    alarms = client.get_alarms()
    alarm_aktiv = len(alarms) > 0
    alarm_typ = ", ".join(client.get_alarm_types()) if alarm_aktiv else None
    raw = client.get_status()

    write_reading(
        device_id=device.id,
        temp=temp,
        humidity=humidity,
        alarm_aktiv=alarm_aktiv,
        alarm_typ=alarm_typ,
        raw=raw,
    )

    status_str = f"T={temp}°C  H={humidity}%"
    if alarm_aktiv:
        logger.warning(f"[ALARM] {device.hostname}: {alarm_typ}  |  {status_str}")
    else:
        logger.info(f"[OK]    {device.hostname}: {status_str}")


def poll_all():
    """Alle Kentix-Geräte einmal abfragen."""
    devices = get_kentix_devices()
    if not devices:
        logger.warning("Keine Kentix-Geräte in DB gefunden.")
        return
    for d in devices:
        try:
            poll_device(d)
        except Exception as e:
            logger.error(f"Fehler bei {d.hostname}: {e}")


# ══════════════════════════════════════════════════════════════
# MAIN — kontinuierlicher Poller
# ══════════════════════════════════════════════════════════════


def run_poller():
    """Dauerhafter Polling-Loop (für systemd-Service oder screen)."""
    logger.info(f"Kentix-Poller gestartet. Intervall: {POLL_INTERVAL_SEC}s")
    while True:
        poll_all()
        time.sleep(POLL_INTERVAL_SEC)


# ══════════════════════════════════════════════════════════════
# CLI-Wrapper (direkt aufrufbar)
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import typer

    ktx_app = typer.Typer(help="Kentix CLI")

    @ktx_app.command("poll")
    def cmd_poll():
        """Einmalig alle Kentix-Geräte abfragen."""
        poll_all()

    @ktx_app.command("daemon")
    def cmd_daemon():
        """Dauerhafter Polling-Loop starten."""
        run_poller()

    @ktx_app.command("status")
    def cmd_status(device_id: int = typer.Argument(...)):
        """Status eines einzelnen Kentix-Geräts anzeigen."""
        with Session(engine) as s:
            d = s.get(Device, device_id)
        if not d:
            typer.echo(f"Gerät {device_id} nicht gefunden.")
            raise typer.Exit(1)
        client = KentixClient(base_url=d.api_url, api_key=d.api_key)
        from rich import print as rprint
        from rich.pretty import Pretty

        rprint(Pretty(client.get_status()))

    ktx_app()
