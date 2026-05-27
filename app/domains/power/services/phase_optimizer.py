from dataclasses import dataclass
from app.domains.power.services.usv_calc import PhaseBalancer


@dataclass
class Empfehlung:
    device_id: int
    hostname: str
    alte_phase: str
    neue_phase: str
    load_watt: float


@dataclass
class OptimizeResult:
    vorher_imbalance_pct: float
    nachher_imbalance_pct: float
    empfehlungen: list[Empfehlung]
    balanced: bool


def optimize_phases(devices: list) -> OptimizeResult:
    result = PhaseBalancer.calculate_balancing(devices)
    empfehlungen = [
        Empfehlung(
            device_id=r["device_id"],
            hostname=r["hostname"],
            alte_phase=r["from_phase"],
            neue_phase=r["to_phase"],
            load_watt=r["load_watt"],
        )
        for r in result["recommendations"]
    ]
    return OptimizeResult(
        vorher_imbalance_pct=result["initial_imbalance_pct"],
        nachher_imbalance_pct=result["final_imbalance_pct"],
        empfehlungen=empfehlungen,
        balanced=result["balanced"],
    )
