from decimal import Decimal
import math
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import (
    UsvUnit,
    Device,
)


class UsvCalculator:
    @staticmethod
    def calculate_n1_required_modules(
        l1_kw: Decimal, l2_kw: Decimal, l3_kw: Decimal, module_capacity_kw: Decimal
    ) -> int:
        """
        Calculates the number of modules required to achieve N+1 redundancy.
        Formula:
        M = ceil(max(P_total / C, 3 * P_max_phase / C)) + 1
        """
        if module_capacity_kw <= 0:
            return 0

        p_total = l1_kw + l2_kw + l3_kw
        p_max_phase = max(l1_kw, l2_kw, l3_kw)

        # Calculate modules needed for total power
        modules_total = p_total / module_capacity_kw
        # Calculate modules needed for worst-case phase balance
        modules_phase = (Decimal("3") * p_max_phase) / module_capacity_kw

        max_needed = max(modules_total, modules_phase)

        ceil_needed = int(math.ceil(float(max_needed)))

        # N+1 requires adding 1 extra module
        return ceil_needed + 1

    @classmethod
    async def get_usv_load_and_status(
        cls, usv_unit_id: int, db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Retrieves the UPS unit, calculates current phase loads by aggregating connected devices,
        and evaluates N+1 status.
        """
        # Fetch USV unit with modules
        query = (
            select(UsvUnit)
            .where(UsvUnit.id == usv_unit_id)
            .options(selectinload(UsvUnit.modules))
        )
        result = await db.execute(query)
        usv_unit = result.scalar_one_or_none()

        if not usv_unit:
            return {"error": "USV unit not found"}

        # Active modules details
        active_modules = [m for m in usv_unit.modules if m.status == "aktiv"]
        installed_kw = sum(m.leistung_kw for m in active_modules)

        # Find the largest module capacity to subtract for N-1
        largest_module_kw = max(
            (m.leistung_kw for m in active_modules), default=Decimal("0")
        )
        n1_kw = max(Decimal("0"), installed_kw - largest_module_kw)

        # Find all devices in the same rack as the UPS
        rack_id = usv_unit.rack_id

        device_query = select(Device).where(Device.rack_id == rack_id)
        device_result = await db.execute(device_query)
        devices = device_result.scalars().all()

        # Initialize phase power aggregators (in kW)
        l1_load = Decimal("0")
        l2_load = Decimal("0")
        l3_load = Decimal("0")

        l1_peak = Decimal("0")
        l2_peak = Decimal("0")
        l3_peak = Decimal("0")

        device_details = []

        if devices:
            for device in devices:
                # Priorisierung: 1. psu_nennwatt * last_pct, 2. tdp_watt, 3. anschlussleistung_watt
                if device.psu_nennwatt is not None:
                    last_pct = device.last_pct if device.last_pct is not None else 60.0
                    effective_watt = Decimal(str(device.psu_nennwatt)) * Decimal(str(last_pct)) / Decimal("100.0")
                elif device.tdp_watt is not None:
                    effective_watt = Decimal(str(device.tdp_watt))
                else:
                    effective_watt = Decimal(str(device.anschlussleistung_watt or 0))

                if not effective_watt:
                    continue

                kw_load = effective_watt / Decimal("1000")
                peak_factor = device.einschaltstrom_faktor or Decimal("2.5")
                kw_peak = kw_load * peak_factor

                phase = device.phase or "L1"  # Default fallback
                if phase == "L1":
                    l1_load += kw_load
                    l1_peak += kw_peak
                elif phase == "L2":
                    l2_load += kw_load
                    l2_peak += kw_peak
                elif phase == "L3":
                    l3_load += kw_load
                    l3_peak += kw_peak

                device_details.append(
                    {
                        "id": device.id,
                        "hostname": device.hostname,
                        "phase": phase,
                        "anschlussleistung_watt": effective_watt,
                        "load_kw": kw_load,
                        "peak_kw": kw_peak,
                    }
                )

        total_load_kw = l1_load + l2_load + l3_load
        total_peak_kw = l1_peak + l2_peak + l3_peak

        # Check N+1 safety:
        # Total load must be <= N-1 capacity
        # Each individual phase load must be <= (N-1 capacity / 3)
        # Note: Peak load is used for Cold Start (Kaltstart) safety check
        # Quick Win 3: USVs can typically handle 150% overload for short durations
        installed_peak_cap = installed_kw * Decimal("1.5")
        phase_peak_cap = (
            installed_peak_cap / Decimal("3")
            if installed_peak_cap > 0
            else Decimal("0")
        )

        phase_capacity_n1 = n1_kw / Decimal("3") if n1_kw > 0 else Decimal("0")

        max_active_phase_load = max(l1_load, l2_load, l3_load)
        max_active_phase_peak = max(l1_peak, l2_peak, l3_peak)

        n1_safe_normal = (total_load_kw <= n1_kw) and (
            max_active_phase_load <= phase_capacity_n1
        )
        kaltstart_ok = (total_peak_kw <= installed_peak_cap) and (
            max_active_phase_peak <= phase_peak_cap
        )

        # Calculate balance and recommended modules
        imbalance = max_active_phase_load - min(l1_load, l2_load, l3_load)

        # Recommended module size is usually the size of modules currently used or default 10kW
        rec_module_capacity = (
            largest_module_kw if largest_module_kw > 0 else Decimal("10")
        )
        recommended_modules = cls.calculate_n1_required_modules(
            l1_load, l2_load, l3_load, rec_module_capacity
        )

        return {
            "usv_unit_id": usv_unit_id,
            "bezeichnung": usv_unit.bezeichnung,
            "installed_kw": installed_kw,
            "n1_kw": n1_kw,
            "phase_capacity_n1_kw": phase_capacity_n1,
            "loads": {
                "l1": {"load_kw": l1_load, "peak_kw": l1_peak},
                "l2": {"load_kw": l2_load, "peak_kw": l2_peak},
                "l3": {"load_kw": l3_load, "peak_kw": l3_peak},
            },
            "total_load_kw": total_load_kw,
            "total_peak_kw": total_peak_kw,
            "imbalance_kw": imbalance,
            "n1_safe": bool(n1_safe_normal),
            "kaltstart_ok": bool(kaltstart_ok),
            "recommended_modules_count": recommended_modules,
            "recommended_module_capacity_kw": rec_module_capacity,
            "active_modules_count": len(active_modules),
            "devices": device_details,
        }

    @classmethod
    def simulate_sandbox_usv(
        cls,
        l1_kw: Decimal,
        l2_kw: Decimal,
        l3_kw: Decimal,
        module_capacity_kw: Decimal,
        installed_modules_count: int,
    ) -> Dict[str, Any]:
        """
        Simulates UPS status based on manual phase load inputs (sandbox).
        """
        installed_kw = Decimal(str(installed_modules_count)) * module_capacity_kw
        n1_kw = max(Decimal("0"), installed_kw - module_capacity_kw)
        phase_capacity_n1 = n1_kw / Decimal("3") if n1_kw > 0 else Decimal("0")

        total_load_kw = l1_kw + l2_kw + l3_kw
        max_phase_load = max(l1_kw, l2_kw, l3_kw)

        n1_safe = (total_load_kw <= n1_kw) and (max_phase_load <= phase_capacity_n1)
        imbalance = max_phase_load - min(l1_kw, l2_kw, l3_kw)

        recommended_modules = cls.calculate_n1_required_modules(
            l1_kw, l2_kw, l3_kw, module_capacity_kw
        )

        return {
            "installed_kw": installed_kw,
            "n1_kw": n1_kw,
            "phase_capacity_n1_kw": phase_capacity_n1,
            "loads": {
                "l1": l1_kw,
                "l2": l2_kw,
                "l3": l3_kw,
            },
            "total_load_kw": total_load_kw,
            "imbalance_kw": imbalance,
            "n1_safe": bool(n1_safe),
            "recommended_modules_count": recommended_modules,
            "installed_modules_count": installed_modules_count,
            "module_capacity_kw": module_capacity_kw,
        }


class FaultSimulationEngine:
    """
    Fault injection engine for UPS N+1 sandbox simulation.
    Supports sequential faults: reset -> grid_failure -> battery_defect -> module_failure.
    Uses Peukert's law for battery runtime calculation (VDE 0558 compliant).
    """

    # --- Battery runtime (Peukert) ---

    @staticmethod
    def calculate_battery_runtime_peukert(
        total_load_kw: Decimal,
        battery_voltage: Decimal = Decimal("48"),
        battery_capacity_ah: Decimal = Decimal("100"),
        peukert_exponent: Decimal = Decimal("1.2"),
        inverter_efficiency: Decimal = Decimal("0.90"),
    ) -> Decimal:
        """
        Peukert's law: t = C_nom * (I_nom / I)^(k-1) / I  [hours].

        Returns runtime in minutes.
        """
        if total_load_kw <= 0:
            return Decimal("9999")

        rated_disposal_hours = Decimal("10")
        i_rated = battery_capacity_ah / rated_disposal_hours
        i_load = (total_load_kw * Decimal("1000")) / (
            battery_voltage * inverter_efficiency
        )

        try:
            t_hours = (
                float(battery_capacity_ah)
                * (float(i_rated) ** (float(peukert_exponent) - 1.0))
                / (float(i_load) ** float(peukert_exponent))
            )
        except (ZeroDivisionError, OverflowError):
            return Decimal("0")

        return Decimal(str(round(t_hours * 60.0, 1)))

    # --- Build baseline state ---

    @classmethod
    def _build_base_state(
        cls,
        l1_kw: Decimal,
        l2_kw: Decimal,
        l3_kw: Decimal,
        module_capacity_kw: Decimal,
        installed_modules_count: int,
        battery_voltage: Decimal,
        battery_capacity_ah: Decimal,
        peukert_exponent: Decimal,
        inverter_efficiency: Decimal,
    ) -> Dict[str, Any]:
        installed_kw = Decimal(str(installed_modules_count)) * module_capacity_kw
        n1_kw = (
            max(Decimal("0"), installed_kw - module_capacity_kw)
            if installed_modules_count >= 2
            else Decimal("0")
        )
        phase_capacity_n1 = n1_kw / Decimal("3") if n1_kw > 0 else Decimal("0")

        total_load = l1_kw + l2_kw + l3_kw
        max_phase = max(l1_kw, l2_kw, l3_kw)
        min_phase = min(l1_kw, l2_kw, l3_kw)

        n1_safe = (total_load <= n1_kw) and (max_phase <= phase_capacity_n1)

        if not n1_safe and total_load > installed_kw:
            status = "critical"
        elif not n1_safe:
            status = "degraded"
        else:
            status = "stable"

        battery_runtime = cls.calculate_battery_runtime_peukert(
            total_load,
            battery_voltage,
            battery_capacity_ah,
            peukert_exponent,
            inverter_efficiency,
        )

        return {
            "status": status,
            "grid_online": True,
            "battery_soc_pct": Decimal("100"),
            "battery_runtime_min": battery_runtime,
            "loads": {
                "l1": float(l1_kw),
                "l2": float(l2_kw),
                "l3": float(l3_kw),
            },
            "total_load_kw": float(total_load),
            "installed_kw": float(installed_kw),
            "n1_kw": float(n1_kw),
            "phase_capacity_n1_kw": float(phase_capacity_n1),
            "n1_safe": n1_safe,
            "imbalance_kw": float(max_phase - min_phase),
            "installed_modules_count": installed_modules_count,
            "active_modules_count": installed_modules_count,
            "failed_modules_count": 0,
            "module_capacity_kw": float(module_capacity_kw),
            "battery_voltage": float(battery_voltage),
            "battery_capacity_ah": float(battery_capacity_ah),
            "peukert_exponent": float(peukert_exponent),
            "inverter_efficiency": float(inverter_efficiency),
        }

    # --- Fault: Grid Failure ---

    @classmethod
    def _apply_grid_failure(
        cls,
        state: Dict[str, Any],
        l1: Decimal,
        l2: Decimal,
        l3: Decimal,
        bv: Decimal,
        bah: Decimal,
        pk: Decimal,
        ie: Decimal,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        s = dict(state)
        s["grid_online"] = False

        total = l1 + l2 + l3
        runtime = cls.calculate_battery_runtime_peukert(total, bv, bah, pk, ie)
        s["battery_runtime_min"] = float(runtime)

        if s["n1_safe"]:
            s["status"] = "degraded"
            desc = (
                f"Netzausfall! Batteriebetrieb aktiv. "
                f"Verbleibende Laufzeit: {runtime} min. N+1 bleibt erfüllt."
            )
            sev = "warning"
        elif s["total_load_kw"] <= s["installed_kw"]:
            s["status"] = "degraded"
            desc = (
                f"Netzausfall! Batteriebetrieb aktiv. {runtime} min Laufzeit. "
                f"ACHTUNG: N+1 nicht mehr gegeben!"
            )
            sev = "warning"
        else:
            s["status"] = "critical"
            desc = (
                f"Netzausfall! Batteriebetrieb. {runtime} min. "
                f"KRITISCH: Last ueberschreitet installierte Leistung!"
            )
            sev = "critical"

        event = {"event_type": "grid_failure", "severity": sev, "description": desc}
        return s, event

    # --- Fault: Battery Defect ---

    @classmethod
    def _apply_battery_defect(
        cls,
        state: Dict[str, Any],
        bv: Decimal,
        bah: Decimal,
        pk: Decimal,
        ie: Decimal,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        s = dict(state)
        effective_ah = Decimal(str(s["battery_capacity_ah"])) * Decimal("0.5")
        s["battery_capacity_ah"] = float(effective_ah)
        s["battery_soc_pct"] = Decimal("50")

        total = Decimal(str(s["total_load_kw"]))
        runtime = cls.calculate_battery_runtime_peukert(total, bv, effective_ah, pk, ie)
        s["battery_runtime_min"] = float(runtime)

        if s["grid_online"]:
            s["status"] = "degraded"
            desc = (
                f"Batterie-Defekt! Kapazitaet halbiert auf {effective_ah} Ah. "
                f"Netz noch verfuegbar, keine sofortige Gefahr."
            )
            sev = "warning"
        else:
            s["status"] = "critical"
            desc = f"Batterie-Defekt bei Netzausfall! Nur noch {runtime} min. KRITISCH!"
            sev = "critical"

        event = {"event_type": "battery_defect", "severity": sev, "description": desc}
        return s, event

    # --- Fault: Module Failure ---

    @classmethod
    def _apply_module_failure(
        cls,
        state: Dict[str, Any],
        l1: Decimal,
        l2: Decimal,
        l3: Decimal,
        module_capacity_kw: Decimal,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        s = dict(state)
        failed = s["failed_modules_count"] + 1
        remaining = s["installed_modules_count"] - failed

        if remaining < 0:
            event = {
                "event_type": "module_failure_rejected",
                "severity": "info",
                "description": "Kein aktives Modul mehr vorhanden, das ausfallen kann.",
            }
            return s, event

        installed_kw = Decimal(str(remaining)) * module_capacity_kw
        n1_kw = (
            max(Decimal("0"), installed_kw - module_capacity_kw)
            if remaining >= 2
            else Decimal("0")
        )
        phase_cap = n1_kw / Decimal("3") if n1_kw > 0 else Decimal("0")

        total = l1 + l2 + l3
        max_ph = max(l1, l2, l3)
        n1_s = (total <= n1_kw) and (max_ph <= phase_cap)

        s["installed_kw"] = float(installed_kw)
        s["n1_kw"] = float(n1_kw)
        s["phase_capacity_n1_kw"] = float(phase_cap)
        s["n1_safe"] = n1_s
        s["failed_modules_count"] = failed
        s["active_modules_count"] = remaining

        if n1_s:
            s["status"] = "stable"
            desc = (
                f"Modul #{failed} ausgefallen. {remaining}/{s['installed_modules_count']} "
                f"aktiv. N+1 weiterhin erfuellt."
            )
            sev = "info"
        elif total > installed_kw:
            s["status"] = "critical"
            desc = (
                f"Modul #{failed} ausgefallen. {remaining}/{s['installed_modules_count']} "
                f"aktiv. KRITISCH: Last > installierte Leistung!"
            )
            sev = "critical"
        else:
            s["status"] = "degraded"
            desc = (
                f"Modul #{failed} ausgefallen. {remaining}/{s['installed_modules_count']} "
                f"aktiv. N+1 NICHT MEHR erfuellt."
            )
            sev = "warning"

        event = {"event_type": "module_failure", "severity": sev, "description": desc}
        return s, event

    # --- Main entry point ---

    @classmethod
    def simulate_fault(
        cls,
        fault_type: str,
        l1_kw: Decimal,
        l2_kw: Decimal,
        l3_kw: Decimal,
        module_capacity_kw: Decimal,
        installed_modules_count: int,
        system_state: Optional[Dict[str, Any]] = None,
        battery_voltage: Decimal = Decimal("48"),
        battery_capacity_ah: Decimal = Decimal("100"),
        peukert_exponent: Decimal = Decimal("1.2"),
        inverter_efficiency: Decimal = Decimal("0.90"),
    ) -> Dict[str, Any]:
        """
        Apply a fault to the current system state (or build baseline for 'reset').

        Returns {"system_state": {...}, "event": {...}}.
        The caller persists events to DB via UsvSimulationEvent.
        """
        state = system_state

        if fault_type == "reset" or state is None:
            state = cls._build_base_state(
                l1_kw,
                l2_kw,
                l3_kw,
                module_capacity_kw,
                installed_modules_count,
                battery_voltage,
                battery_capacity_ah,
                peukert_exponent,
                inverter_efficiency,
            )
            event = {
                "event_type": "simulation_reset",
                "severity": "info",
                "description": (
                    f"System initialisiert: {installed_modules_count} Module a "
                    f"{module_capacity_kw} kW, "
                    f"N+1 {'sicher' if state['n1_safe'] else 'UNSICHER'}, "
                    f"Batterielaufzeit {state['battery_runtime_min']} min bei "
                    f"{state['total_load_kw']} kW Last"
                ),
            }
            return {"system_state": state, "event": event}

        assert state is not None

        if fault_type == "grid_failure":
            new_state, event = cls._apply_grid_failure(
                state,
                l1_kw,
                l2_kw,
                l3_kw,
                battery_voltage,
                battery_capacity_ah,
                peukert_exponent,
                inverter_efficiency,
            )
        elif fault_type == "battery_defect":
            new_state, event = cls._apply_battery_defect(
                state,
                battery_voltage,
                battery_capacity_ah,
                peukert_exponent,
                inverter_efficiency,
            )
        elif fault_type == "module_failure":
            new_state, event = cls._apply_module_failure(
                state,
                l1_kw,
                l2_kw,
                l3_kw,
                module_capacity_kw,
            )
        else:
            new_state = state
            event = {
                "event_type": "unknown_fault",
                "severity": "warning",
                "description": f"Unbekannter Fehlertyp: {fault_type}",
            }

        return {"system_state": new_state, "event": event}


# === BATTERY CABINET CONFIGURATION & CALCULATIONS ===

BATTERY_TYPE_PROFILES: Dict[str, Dict[str, Any]] = {
    "lead_acid": {
        "name": "Blei-Säure",
        "peukert_k": Decimal("1.20"),
        "lifespan_years": 5,
        "temp_coeff_per_10c": Decimal("-0.020"),
        "aging_base": Decimal("0.80"),
        "aging_divisor": 5,
    },
    "vrla": {
        "name": "VRLA",
        "peukert_k": Decimal("1.15"),
        "lifespan_years": 8,
        "temp_coeff_per_10c": Decimal("-0.015"),
        "aging_base": Decimal("0.85"),
        "aging_divisor": 5,
    },
    "li_ion": {
        "name": "Li-Ion",
        "peukert_k": Decimal("1.05"),
        "lifespan_years": 15,
        "temp_coeff_per_10c": Decimal("-0.005"),
        "aging_base": Decimal("0.95"),
        "aging_divisor": 10,
    },
    "nicd": {
        "name": "NiCd",
        "peukert_k": Decimal("1.10"),
        "lifespan_years": 20,
        "temp_coeff_per_10c": Decimal("-0.010"),
        "aging_base": Decimal("0.88"),
        "aging_divisor": 5,
    },
}


class BatteryCabinetEngine:
    """Battery cabinet simulation: block config, aging, temperature, runtime curves."""

    @staticmethod
    def get_profile(battery_type: str) -> Dict[str, Any]:
        return BATTERY_TYPE_PROFILES.get(battery_type, BATTERY_TYPE_PROFILES["vrla"])

    @staticmethod
    def calculate_effective_capacity(
        battery_type: str,
        series_blocks: int,
        parallel_strings: int,
        block_voltage_v: Decimal = Decimal("12"),
        block_capacity_ah: Decimal = Decimal("100"),
        age_years: Decimal = Decimal("0"),
        temperature_c: Decimal = Decimal("20"),
    ) -> Dict[str, Any]:
        profile = BatteryCabinetEngine.get_profile(battery_type)

        total_voltage = Decimal(str(series_blocks)) * block_voltage_v
        nominal_capacity_ah = Decimal(str(parallel_strings)) * block_capacity_ah
        nominal_energy_kwh = total_voltage * nominal_capacity_ah / Decimal("1000")

        # Temperature factor: 1.0 at 20°C, linear change
        if temperature_c < Decimal("20"):
            # <20°C -> Capacity loss ca. 1% pro °C unter 20°C
            temp_delta = Decimal("20") - temperature_c
            temp_factor = Decimal("1") - (temp_delta * Decimal("0.01"))
            temp_factor = max(Decimal("0.5"), temp_factor)
            aging_temp_multiplier = 1.0
        else:
            # >= 20°C -> No capacity loss, but accelerated aging
            temp_factor = Decimal("1")
            if temperature_c > Decimal("25"):
                # Halbierung der Lebensdauer alle 10°C über 25°C
                excess_temp = float(temperature_c - Decimal("25"))
                aging_temp_multiplier = 2.0 ** (excess_temp / 10.0)
            else:
                aging_temp_multiplier = 1.0

        # Aging factor: capacity_degradation = aging_base ^ (age / divisor)
        effective_age = float(age_years) * aging_temp_multiplier
        aging_exp = effective_age / profile["aging_divisor"]
        aging_factor = Decimal(str(round(float(profile["aging_base"]) ** aging_exp, 4)))

        effective_capacity_ah = nominal_capacity_ah * aging_factor * temp_factor
        effective_energy_kwh = total_voltage * effective_capacity_ah / Decimal("1000")

        return {
            "battery_type": battery_type,
            "battery_type_name": profile["name"],
            "total_voltage_v": float(total_voltage),
            "nominal_capacity_ah": float(nominal_capacity_ah),
            "nominal_energy_kwh": float(round(nominal_energy_kwh, 2)),
            "effective_capacity_ah": float(round(effective_capacity_ah, 1)),
            "effective_energy_kwh": float(round(effective_energy_kwh, 2)),
            "aging_factor_pct": float(round(aging_factor * Decimal("100"), 1)),
            "temperature_factor_pct": float(round(temp_factor * Decimal("100"), 1)),
            "peukert_k": float(profile["peukert_k"]),
            "lifespan_years": profile["lifespan_years"],
            "series_blocks": series_blocks,
            "parallel_strings": parallel_strings,
            "total_blocks": series_blocks * parallel_strings,
            "age_years": float(age_years),
            "temperature_c": float(temperature_c),
        }

    @staticmethod
    def calculate_runtime_curve(
        l1_kw: Decimal,
        l2_kw: Decimal,
        l3_kw: Decimal,
        module_capacity_kw: Decimal,
        installed_modules_count: int,
        battery_type: str,
        series_blocks: int,
        parallel_strings: int,
        block_voltage_v: Decimal = Decimal("12"),
        block_capacity_ah: Decimal = Decimal("100"),
        age_years: Decimal = Decimal("0"),
        temperature_c: Decimal = Decimal("20"),
        inverter_efficiency: Decimal = Decimal("0.90"),
    ) -> Dict[str, Any]:
        battery_info = BatteryCabinetEngine.calculate_effective_capacity(
            battery_type,
            series_blocks,
            parallel_strings,
            block_voltage_v,
            block_capacity_ah,
            age_years,
            temperature_c,
        )
        profile = BatteryCabinetEngine.get_profile(battery_type)
        peukert_k = profile["peukert_k"]

        installed_kw = Decimal(str(installed_modules_count)) * module_capacity_kw
        total_load = float(l1_kw + l2_kw + l3_kw)
        runtime_at_current = FaultSimulationEngine.calculate_battery_runtime_peukert(
            Decimal(str(total_load)),
            Decimal(str(battery_info["total_voltage_v"])),
            Decimal(str(battery_info["effective_capacity_ah"])),
            peukert_k,
            inverter_efficiency,
        )

        # Generate curve points from 5% to 150% of installed capacity
        curve_points: List[Dict[str, float]] = []
        step_count = 30
        max_load = float(installed_kw) * 1.5
        for i in range(step_count + 1):
            pct = i / step_count
            load_point = max(float(installed_kw) * 0.02, max_load * pct)
            runtime = FaultSimulationEngine.calculate_battery_runtime_peukert(
                Decimal(str(round(load_point, 2))),
                Decimal(str(battery_info["total_voltage_v"])),
                Decimal(str(battery_info["effective_capacity_ah"])),
                peukert_k,
                inverter_efficiency,
            )
            curve_points.append(
                {
                    "load_kw": round(load_point, 2),
                    "runtime_min": float(runtime),
                    "load_pct": round(load_point / float(installed_kw) * 100, 1)
                    if installed_kw > 0
                    else 0,
                }
            )

        # N+1 status
        n1_kw = (
            float(installed_kw) - float(module_capacity_kw)
            if installed_modules_count >= 2
            else 0
        )
        max_phase = float(max(l1_kw, l2_kw, l3_kw))
        phase_cap = n1_kw / 3 if n1_kw > 0 else 0
        n1_safe = (total_load <= n1_kw) and (max_phase <= phase_cap)

        return {
            "curve": curve_points,
            "battery_summary": battery_info,
            "current_runtime_min": float(runtime_at_current),
            "installed_kw": float(installed_kw),
            "total_load_kw": total_load,
            "n1_kw": n1_kw,
            "n1_safe": n1_safe,
        }

    @staticmethod
    def calculate_dimensioning(
        load_kw: Decimal,
        target_runtime_min: Decimal,
        battery_type: str,
        block_voltage_v: Decimal = Decimal("12"),
        block_capacity_ah: Decimal = Decimal("100"),
        inverter_efficiency: Decimal = Decimal("0.90"),
        system_voltage_v: Decimal = Decimal("48"),
        safety_margin_pct: Decimal = Decimal("0.15"),
    ) -> Dict[str, Any]:
        profile = BatteryCabinetEngine.get_profile(battery_type)
        peukert_k = profile["peukert_k"]

        if load_kw <= 0 or target_runtime_min <= 0:
            return {"error": "Last und Laufzeit muessen > 0 sein"}

        load_with_margin = load_kw * (Decimal("1") + safety_margin_pct)
        target_hours = target_runtime_min / Decimal("60")

        # Invert Peukert: C = I^k * t / (I_n)^(k-1)
        i_load = (load_with_margin * Decimal("1000")) / (
            system_voltage_v * inverter_efficiency
        )
        i_rated = Decimal("0")  # placeholder; we solve iteratively

        # Iterative approach: guess capacity, calculate runtime, adjust
        cap_guess = load_with_margin * target_hours * Decimal("1000") / system_voltage_v
        for _ in range(50):
            i_rated = cap_guess / Decimal("10")
            try:
                t_h = (
                    float(cap_guess)
                    * (float(i_rated) ** (float(peukert_k) - 1.0))
                    / (float(i_load) ** float(peukert_k))
                )
            except (ZeroDivisionError, OverflowError):
                break
            if t_h <= 0:
                cap_guess *= Decimal("1.1")
                continue
            if abs(t_h - float(target_hours)) < 0.001:
                break
            cap_guess = cap_guess * Decimal(str(float(target_hours) / t_h))

        required_ah = max(Decimal("1"), cap_guess)
        series_blocks = int(float(system_voltage_v / block_voltage_v))
        if series_blocks < 1:
            series_blocks = 1
        parallel_strings = max(
            1, int(math.ceil(float(required_ah / block_capacity_ah)))
        )
        total_blocks = series_blocks * parallel_strings
        actual_capacity_ah = Decimal(str(parallel_strings)) * block_capacity_ah

        # Verify with actual config
        v_actual = FaultSimulationEngine.calculate_battery_runtime_peukert(
            load_with_margin,
            system_voltage_v,
            actual_capacity_ah,
            peukert_k,
            inverter_efficiency,
        )

        return {
            "required_capacity_ah": float(round(required_ah, 1)),
            "series_blocks": series_blocks,
            "parallel_strings": parallel_strings,
            "total_blocks": total_blocks,
            "actual_capacity_ah": float(actual_capacity_ah),
            "actual_runtime_min": float(v_actual),
            "system_voltage_v": float(system_voltage_v),
            "block_voltage_v": float(block_voltage_v),
            "block_capacity_ah": float(block_capacity_ah),
            "target_runtime_min": float(target_runtime_min),
            "load_kw": float(load_kw),
            "load_with_margin_kw": float(round(load_with_margin, 2)),
            "safety_margin_pct": float(safety_margin_pct * Decimal("100")),
            "battery_type": battery_type,
            "battery_type_name": profile["name"],
        }


class ShutdownSimulationEngine:
    """
    Simulates battery discharge and controlled server shutdown timeline.
    Accounts for load drop as servers turn off, recalculating Peukert runtime.
    """

    @staticmethod
    def simulate_shutdown(
        battery_type: str,
        series_blocks: int,
        parallel_strings: int,
        block_voltage_v: Decimal,
        block_capacity_ah: Decimal,
        age_years: Decimal,
        temperature_c: Decimal,
        inverter_efficiency: Decimal,
        devices: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        # Calculate initial capacity
        battery_info = BatteryCabinetEngine.calculate_effective_capacity(
            battery_type=battery_type,
            series_blocks=series_blocks,
            parallel_strings=parallel_strings,
            block_voltage_v=block_voltage_v,
            block_capacity_ah=block_capacity_ah,
            age_years=age_years,
            temperature_c=temperature_c,
        )

        effective_ah = Decimal(str(battery_info["effective_capacity_ah"]))
        total_voltage_v = Decimal(str(battery_info["total_voltage_v"]))
        profile = BatteryCabinetEngine.get_profile(battery_type)
        peukert_k = profile["peukert_k"]

        # Rated discharge parameters
        rated_hours = Decimal("10.0")
        i_rated = effective_ah / rated_hours

        # Setup simulation state
        c_remaining = effective_ah
        timeline: List[Dict[str, Any]] = []
        device_statuses: Dict[int, Dict[str, Any]] = {}

        # Initialize all devices as successful first
        for dev in devices:
            device_statuses[dev["id"]] = {
                "id": dev["id"],
                "hostname": dev["hostname"],
                "tdp_watt": float(dev.get("tdp_watt") or 0),
                "shutdown_delay_seconds": dev.get("shutdown_delay_seconds") or 0,
                "shutdown_priority": dev.get("shutdown_priority") or 2,
                "crashed": False,
                "crash_reason": None,
                "shutdown_at_seconds": None,
            }

        step_seconds = 10
        t = 0
        max_duration_seconds = 3600 * 5  # 5 hours max safety limit

        while t <= max_duration_seconds:
            # Determine which devices are still active at time t
            active_devices = []
            inactive_devices = []
            for dev in devices:
                delay = dev.get("shutdown_delay_seconds") or 0
                if t < delay:
                    active_devices.append(dev)
                else:
                    inactive_devices.append(dev)
                    if device_statuses[dev["id"]]["shutdown_at_seconds"] is None:
                        device_statuses[dev["id"]]["shutdown_at_seconds"] = delay

            active_load_watt = sum(
                Decimal(str(d.get("tdp_watt") or 0)) for d in active_devices
            )
            active_load_kw = active_load_watt / Decimal("1000")

            battery_empty = c_remaining <= 1
            if battery_empty:
                for dev in active_devices:
                    device_statuses[dev["id"]]["crashed"] = True
                    device_statuses[dev["id"]]["crash_reason"] = "Akku leer"
                active_devices = []

            all_shut_down = len(active_devices) == 0 and t > 0

            runtime_capacity = max(Decimal("0.001"), c_remaining)
            remaining_runtime_min = (
                FaultSimulationEngine.calculate_battery_runtime_peukert(
                    total_load_kw=active_load_kw,
                    battery_voltage=total_voltage_v,
                    battery_capacity_ah=runtime_capacity,
                    peukert_exponent=peukert_k,
                    inverter_efficiency=inverter_efficiency,
                )
            )

            soc_pct = (
                (c_remaining / effective_ah) * Decimal("100")
                if effective_ah > 0
                else Decimal("0")
            )
            timeline.append(
                {
                    "time_seconds": t,
                    "soc_pct": float(round(max(Decimal("0"), soc_pct), 2)),
                    "load_kw": float(round(active_load_kw, 3)),
                    "remaining_runtime_min": float(remaining_runtime_min),
                    "active_device_ids": [d["id"] for d in active_devices],
                }
            )

            if battery_empty or all_shut_down:
                break

            if active_load_kw > 0:
                i_load = (active_load_kw * Decimal("1000")) / (
                    total_voltage_v * inverter_efficiency
                )
                try:
                    i_peukert = i_load * (i_load / i_rated) ** (
                        peukert_k - Decimal("1")
                    )
                    ah_consumed = i_peukert * Decimal(str(step_seconds / 3600.0))
                    c_remaining -= ah_consumed
                except Exception:
                    c_remaining = Decimal("0")
            else:
                pass

            t += step_seconds

        return {
            "battery_summary": battery_info,
            "timeline": timeline,
            "device_statuses": list(device_statuses.values()),
        }
