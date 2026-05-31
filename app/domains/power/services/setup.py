from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.power.models import (
    DistributionCircuit,
    DistributionPanel,
    UsvModule,
    UsvUnit,
)
from app.domains.hardware.models import Device  # für Last-Erfassung am Rack

from app.domains.power.schemas import (
    PowerMetrics,
    UsvSystemSetupRequest,
    UsvSystemSetupResponse,
)
from app.domains.power.metrics import (
    DeviceLoad,
    ModuleSpec,
    calculate_power_metrics,
)


class UsvUnitExists(Exception):
    """Eine UsvUnit mit (bezeichnung, rack_id) existiert bereits."""

    def __init__(self, bezeichnung: str, rack_id: int):
        self.bezeichnung = bezeichnung
        self.rack_id = rack_id
        super().__init__(
            f"USV '{bezeichnung}' in Rack {rack_id} existiert bereits."
        )


async def setup_usv_system(
    db: AsyncSession,
    setup: UsvSystemSetupRequest,
) -> UsvSystemSetupResponse:
    """
    Erzeugt USV-Schrank + Module + Unterverteilung + Stromkreise in EINER
    Transaktion. Gibt die erzeugten IDs plus Simulations-Kennzahlen zurück.

    Der Aufrufer (Router) ist NICHT für commit/rollback zuständig — das macht
    diese Funktion, damit die alles-oder-nichts-Garantie hier gekapselt bleibt.
    """
    # ── [0/4] Upsert-Key: Duplikat-Check ───────────────────────
    existing = await db.scalar(
        select(UsvUnit.id).where(
            UsvUnit.bezeichnung == setup.usv_bezeichnung,
            UsvUnit.rack_id == setup.rack_id,
        )
    )
    if existing is not None:
        # Noch nichts geschrieben → kein rollback nötig, aber sauber bleiben.
        raise UsvUnitExists(setup.usv_bezeichnung, setup.rack_id)

    try:
        # ── [1/4] UsvUnit ──────────────────────────────────────
        unit = UsvUnit(
            bezeichnung=setup.usv_bezeichnung,
            hersteller=setup.hersteller,
            rack_id=setup.rack_id,
            max_kw=setup.usv_kw,
            geaendert_von=setup.geaendert_von,
        )
        db.add(unit)
        await db.flush()  # → unit.id für die Module-FKs

        # ── [2/4] UsvModule (aktiv + reserve) ──────────────────
        module_ids: list[int] = []
        slot = 1
        for _ in range(setup.module_count):
            m = UsvModule(
                usv_unit_id=unit.id,
                slot=slot,
                leistung_kw=setup.module_kw,
                status="aktiv",
                geaendert_von=setup.geaendert_von,
            )
            db.add(m)
            slot += 1
        for _ in range(setup.reserve_module_count):
            m = UsvModule(
                usv_unit_id=unit.id,
                slot=slot,
                leistung_kw=setup.module_kw,
                status="reserve",
                geaendert_von=setup.geaendert_von,
            )
            db.add(m)
            slot += 1
        await db.flush()  # → module IDs
        # IDs einsammeln (nach flush verfügbar)
        result = await db.scalars(
            select(UsvModule.id).where(UsvModule.usv_unit_id == unit.id)
        )
        module_ids = list(result)

        # ── [3/4] DistributionPanel ────────────────────────────
        panel = DistributionPanel(
            bezeichnung=setup.panel_bezeichnung,
            rack_id=setup.rack_id,
            usv_unit_id=unit.id,
            geaendert_von=setup.geaendert_von,
        )
        db.add(panel)
        await db.flush()  # → panel.id für die Circuit-FKs

        # ── [4/4] DistributionCircuit je Phase ─────────────────
        circuit_ids: list[int] = []
        for idx, phase in enumerate(setup.phases, start=1):
            c = DistributionCircuit(
                panel_id=panel.id,
                bezeichnung=f"Schiene {phase}-{idx:02d}",
                phase=phase,
                absicherung_a=setup.absicherung_a,
            )
            db.add(c)
        await db.flush()
        result = await db.scalars(
            select(DistributionCircuit.id).where(
                DistributionCircuit.panel_id == panel.id
            )
        )
        circuit_ids = list(result)

        # ── Simulation: Kennzahlen aus der gerade gebauten Konfig ──
        # Module aus dem Request (aktiv) speisen die N+1-Rechnung.
        active_modules = [
            ModuleSpec(leistung_kw=float(setup.module_kw))
            for _ in range(setup.module_count)
        ]
        # Last aus real am Rack dokumentierten Geräten (kann leer sein).
        dev_rows = await db.scalars(
            select(Device).where(
                Device.rack_id == setup.rack_id,
                Device.tdp_watt.isnot(None),
            )
        )
        device_loads = [
            DeviceLoad(
                tdp_watt=float(d.tdp_watt),
                phase=d.phase,
                einschaltstrom_faktor=float(d.einschaltstrom_faktor or 2.5) if hasattr(d, 'einschaltstrom_faktor') else 2.5,
            )
            for d in dev_rows
        ]
        metrics_result = calculate_power_metrics(device_loads, active_modules)

        # ── EIN commit am Ende ─────────────────────────────────
        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return UsvSystemSetupResponse(
        usv_unit_id=unit.id,
        module_ids=module_ids,
        panel_id=panel.id,
        circuit_ids=circuit_ids,
        metrics=PowerMetrics(
            last_kw=metrics_result.last_kw,
            peak_kw=metrics_result.peak_kw,
            installiert_kw=metrics_result.installiert_kw,
            n1_kw=metrics_result.n1_kw,
            reserve_kw=metrics_result.reserve_kw,
            groesstes_modul_kw=metrics_result.groesstes_modul_kw,
            kaltstart_ok=metrics_result.kaltstart_ok,
            phasen_last_kw=metrics_result.phasen_last_kw,
            phasen_imbalance_pct=metrics_result.phasen_imbalance_pct,
        ),
        warnings=metrics_result.hinweise,
    )
