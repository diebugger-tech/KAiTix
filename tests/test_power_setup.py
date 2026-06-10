"""
tests/test_power_setup.py

Deckt die im Review (Punkt 3) geforderten Pfade ab:
- Reine Berechnung calculate_power_metrics (kein DB, schnell, deterministisch)
- Service-Rollback: Fehler in Schritt [3/4] → keine Unit/Module in der DB
- Duplikat-Check: zweiter Setup mit gleichem (bezeichnung, rack_id) → UsvUnitExists

Die Berechnungs-Tests laufen ohne DB. Die Service-Tests brauchen eine
async-Session-Fixture (hier als Skizze mit den Projekt-Fixtures angenommen).
"""

from __future__ import annotations

import pytest

from app.domains.power.metrics import (
    DeviceLoad,
    ModuleSpec,
    calculate_power_metrics,
)


# ══════════════════════════════════════════════════════════════
# 1) REINE BERECHNUNG  (keine DB)
# ══════════════════════════════════════════════════════════════
def test_kaltstart_ok_wenn_peak_unter_n1():
    # 4 × 10 kW = 40 installiert; N+1 = 30. Last 8 kW, Peak 8×2.5 = 20 ≤ 30.
    devices = [DeviceLoad(tdp_watt=2000) for _ in range(4)]  # 8 kW gesamt
    modules = [ModuleSpec(leistung_kw=10.0) for _ in range(4)]
    r = calculate_power_metrics(devices, modules)
    assert r.installiert_kw == 40.0
    assert r.n1_kw == 30.0
    assert r.peak_kw == pytest.approx(20.0)
    assert r.kaltstart_ok is True
    assert r.kaltstart_reserve_kw == pytest.approx(10.0)


def test_kaltstart_nicht_ok_erzeugt_hinweis():
    # Peak über N+1 → kaltstart_ok False + Tatsachen-Hinweis (kein Verdikt).
    devices = [DeviceLoad(tdp_watt=8000) for _ in range(2)]  # 16 kW, Peak 40
    modules = [ModuleSpec(leistung_kw=10.0) for _ in range(4)]  # N+1 = 30
    r = calculate_power_metrics(devices, modules)
    assert r.kaltstart_ok is False
    assert any("Kaltstart-Peak" in h for h in r.hinweise)


def test_leere_module_kein_crash():
    r = calculate_power_metrics([DeviceLoad(tdp_watt=1000)], [])
    assert r.n1_kw == 0.0
    assert r.kaltstart_ok is False
    assert any("Keine aktiven Module" in h for h in r.hinweise)


def test_phasen_imbalance_berechnung():
    # Alles auf L1 → maximale Imbalance.
    devices = [
        DeviceLoad(tdp_watt=3000, phase="L1"),
        DeviceLoad(tdp_watt=0, phase="L2"),
        DeviceLoad(tdp_watt=0, phase="L3"),
    ]
    modules = [ModuleSpec(leistung_kw=10.0)]
    r = calculate_power_metrics(devices, modules)
    # ideal = 1 kW, L1 = 3 kW → Abweichung 2 → 200 %
    assert r.phasen_imbalance_pct == pytest.approx(200.0)
    assert any("Imbalance" in h for h in r.hinweise)


def test_ausgewogene_phasen_keine_imbalance_warnung():
    devices = [
        DeviceLoad(tdp_watt=1000, phase="L1"),
        DeviceLoad(tdp_watt=1000, phase="L2"),
        DeviceLoad(tdp_watt=1000, phase="L3"),
    ]
    r = calculate_power_metrics(devices, [ModuleSpec(leistung_kw=10.0)])
    assert r.phasen_imbalance_pct == pytest.approx(0.0)
    assert not any("Imbalance" in h for h in r.hinweise)


# ══════════════════════════════════════════════════════════════
# 2) SERVICE: ROLLBACK-PFAD  (async DB-Fixture vorausgesetzt)
# ══════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_rollback_bei_fehler_in_schritt_3(db, monkeypatch, seed_rack):
    """
    Erzwingt einen Fehler beim Anlegen des DistributionPanel und prüft, dass
    danach KEINE UsvUnit und KEINE Module in der DB liegen (alles-oder-nichts).
    """
    from sqlalchemy import select, func
    from app.domains.power.services import setup
    from app.domains.power.models import UsvUnit, UsvModule
    from app.domains.power.schemas import UsvSystemSetupRequest

    # Panel-Konstruktor sabotieren → Fehler exakt in Schritt [3/4]
    class Boom(Exception):
        pass

    def explode(*args, **kwargs):
        raise Boom("simulierter Panel-Fehler")

    monkeypatch.setattr(setup, "DistributionPanel", explode)

    req = UsvSystemSetupRequest(
        usv_bezeichnung="Rollback-Test",
        usv_kw=40,
        rack_id=seed_rack.id,
        module_kw=10,
        module_count=4,
        panel_bezeichnung="UV-TEST",
        absicherung_a=16,
        geaendert_von="pytest",
    )

    with pytest.raises(Boom):
        await setup.setup_usv_system(db, req)

    # Nach Rollback: nichts persistiert
    units = await db.scalar(
        select(func.count())
        .select_from(UsvUnit)
        .where(UsvUnit.bezeichnung == "Rollback-Test")
    )
    mods = await db.scalar(select(func.count()).select_from(UsvModule))
    assert units == 0
    assert mods == 0


# ══════════════════════════════════════════════════════════════
# 3) SERVICE: DUPLIKAT-CHECK → UsvUnitExists
# ══════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_duplikat_loest_usvunitexists_aus(db, seed_rack):
    from app.domains.power.services.setup import setup_usv_system, UsvUnitExists
    from app.domains.power.schemas import UsvSystemSetupRequest

    req = UsvSystemSetupRequest(
        usv_bezeichnung="Wöhrle 40kW Schrank",
        usv_kw=40,
        rack_id=seed_rack.id,
        module_kw=10,
        module_count=4,
        panel_bezeichnung="UV-RZ-01",
        absicherung_a=16,
        geaendert_von="pytest",
    )

    # Erster Aufruf: ok
    await setup_usv_system(db, req)

    # Zweiter, identischer Aufruf: Konflikt
    with pytest.raises(UsvUnitExists):
        await setup_usv_system(db, req)
