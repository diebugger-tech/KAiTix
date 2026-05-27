import asyncio
import typer
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
import app.models  # Ensure all SQLAlchemy models are registered
from app.domains.power.models import (
    UsvUnit,
    UsvModule,
    DistributionPanel,
    DistributionCircuit,
    UsvCalculation,
)


class ValidationLevel(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass
class ValidationResult:
    level: ValidationLevel
    code: str
    message: str


def audit_vde_compliance(payload: dict) -> list[ValidationResult]:
    results = []
    if payload.get("module_count", 0) < 2:
        results.append(
            ValidationResult(ValidationLevel.ERROR, "N1_IMPOSSIBLE", "Kein N+1 möglich")
        )
    if payload.get("battery_strings", 0) < 2:
        results.append(
            ValidationResult(
                ValidationLevel.ERROR, "BATTERY_SPOF", "SPOF Batteriesystem"
            )
        )
    if not payload.get("has_epo", False):
        results.append(
            ValidationResult(
                ValidationLevel.ERROR,
                "EPO_MISSING",
                "Kein EPO-Kreis — VDE 0108-100 Verstoß",
            )
        )
    if not payload.get("has_bypass", False):
        results.append(
            ValidationResult(
                ValidationLevel.WARNING,
                "MBS_MISSING",
                "Fehlender MBS — Wartung erfordert Downtime",
            )
        )
    return results


app = typer.Typer()


async def async_main(
    rack_id: int,
    usv_bezeichnung: str,
    usv_kw: float,
    module_kw: float,
    module_count: int,
    battery_strings: int,
    has_bypass: bool,
    has_epo: bool,
    phases: str,
    absicherung: float,
    dry_run: bool,
    from_eplan: bool,
):
    if from_eplan:
        raise NotImplementedError("EPLAN CSV-Import folgt in Phase 3")

    payload = {
        "module_count": module_count,
        "battery_strings": battery_strings,
        "has_epo": has_epo,
        "has_bypass": has_bypass,
    }

    audit_results = audit_vde_compliance(payload)
    has_error = False

    for res in audit_results:
        prefix = "❌ FEHLER" if res.level == ValidationLevel.ERROR else "⚠️ WARNUNG"
        print(f"{prefix}: {res.message} ({res.code})")
        if res.level == ValidationLevel.ERROR:
            has_error = True

    if has_error:
        print("Abbruch aufgrund von VDE-Compliance Fehlern.")
        raise typer.Exit(code=1)

    has_warning = any(r.level == ValidationLevel.WARNING for r in audit_results)
    print(f"VDE-Audit: {'WARNUNG' if has_warning else 'BESTANDEN'}")

    if dry_run:
        print("Dry-run aktiviert, keine Datenbankänderungen.")
        return

    async with AsyncSessionLocal() as session:
        # [1/4] USV-Schrank anlegen/updaten
        print("[1/4] USV-Schrank anlegen/updaten...")
        result = await session.execute(
            select(UsvUnit).where(
                UsvUnit.bezeichnung == usv_bezeichnung, UsvUnit.rack_id == rack_id
            )
        )
        usv_unit = result.scalar_one_or_none()

        if usv_unit:
            print("USV-Unit existiert bereits. Führe UPDATE aus.")
            usv_unit.max_kw = usv_kw
            usv_unit.battery_strings = battery_strings
            usv_unit.has_bypass_switch = has_bypass
        else:
            print("Lege neue USV-Unit an.")
            usv_unit = UsvUnit(
                bezeichnung=usv_bezeichnung,
                rack_id=rack_id,
                max_kw=usv_kw,
                battery_strings=battery_strings,
                has_bypass_switch=has_bypass,
                hersteller="Wöhrle SVS",
            )
            session.add(usv_unit)

        await session.commit()
        await session.refresh(usv_unit)

        # [2/4] Module registrieren
        print("[2/4] Module registrieren...")
        for mod in (
            (
                await session.execute(
                    select(UsvModule).where(UsvModule.usv_unit_id == usv_unit.id)
                )
            )
            .scalars()
            .all()
        ):
            await session.delete(mod)
        await session.commit()

        for slot in range(1, module_count + 1):
            status = "reserve" if slot == module_count else "aktiv"
            mod = UsvModule(
                usv_unit_id=usv_unit.id, slot=slot, leistung_kw=module_kw, status=status
            )
            session.add(mod)
        await session.commit()

        # [3/4] DistributionPanel anlegen
        print("[3/4] DistributionPanel anlegen...")
        result = await session.execute(
            select(DistributionPanel).where(
                DistributionPanel.usv_unit_id == usv_unit.id
            )
        )
        panel = result.scalar_one_or_none()
        if not panel:
            panel = DistributionPanel(
                bezeichnung=f"UV-{usv_bezeichnung}",
                rack_id=rack_id,
                usv_unit_id=usv_unit.id,
                has_epo_contact=has_epo,
            )
            session.add(panel)
        else:
            panel.has_epo_contact = has_epo
        await session.commit()
        await session.refresh(panel)

        # [4/4] Stromkreise je Phase aus --phases
        print("[4/4] Stromkreise anlegen...")
        for circ in (
            (
                await session.execute(
                    select(DistributionCircuit).where(
                        DistributionCircuit.panel_id == panel.id
                    )
                )
            )
            .scalars()
            .all()
        ):
            await session.delete(circ)
        await session.commit()

        phase_list = [p.strip() for p in phases.split(",")]
        for p in phase_list:
            circ = DistributionCircuit(
                panel_id=panel.id,
                bezeichnung=f"Stromkreis {p}",
                phase=p,
                absicherung_a=absicherung,
                max_watt=absicherung * 230.0,
            )
            session.add(circ)
        await session.commit()

        # Initialer Snapshot
        print("Erstelle initialen Snapshot in usv_calculations...")
        installiert_kw = float(module_count * module_kw)
        n1_kw = installiert_kw - module_kw
        peak_kw = installiert_kw * 2.5
        last_kw = installiert_kw - module_kw
        reserve_kw = installiert_kw - last_kw
        kaltstart_ok = peak_kw <= n1_kw

        calc = UsvCalculation(
            berechnet_am=datetime.now(timezone.utc),
            usv_unit_id=usv_unit.id,
            installiert_kw=installiert_kw,
            n1_kw=n1_kw,
            peak_kw=peak_kw,
            last_kw=last_kw,
            reserve_kw=reserve_kw,
            kaltstart_ok=kaltstart_ok,
            bemerkung="Initialer Setup durch power_setup_generator",
        )
        session.add(calc)
        await session.commit()

        print("Setup erfolgreich abgeschlossen.")


@app.command()
def main(
    rack_id: int = typer.Option(..., "--rack-id"),
    usv_bezeichnung: str = typer.Option(..., "--usv-bezeichnung"),
    usv_kw: float = typer.Option(..., "--usv-kw"),
    module_kw: float = typer.Option(..., "--module-kw"),
    module_count: int = typer.Option(..., "--module-count"),
    battery_strings: int = typer.Option(..., "--battery-strings"),
    has_bypass: bool = typer.Option(False, "--has-bypass"),
    has_epo: bool = typer.Option(False, "--has-epo"),
    phases: str = typer.Option(..., "--phases"),
    absicherung: float = typer.Option(..., "--absicherung"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    from_eplan: bool = typer.Option(False, "--from-eplan"),
):
    asyncio.run(
        async_main(
            rack_id,
            usv_bezeichnung,
            usv_kw,
            module_kw,
            module_count,
            battery_strings,
            has_bypass,
            has_epo,
            phases,
            absicherung,
            dry_run,
            from_eplan,
        )
    )


if __name__ == "__main__":
    app()
