"""
Anomalie-Scorer für die Topologie-Heatmap.

Berechnet pro Rack einen gewichteten Risiko-Score (0.0–1.0) basierend auf
dokumentierten Daten in der Datenbank — vollständig offline, kein Monitoring.

Scores (gewichtet):
  - Phasen-Imbalance   (25 %) : Ungleichgewicht L1/L2/L3 TDP-Last
  - Überlast           (30 %) : Gesamt-TDP vs. rack.max_watt
  - Kein USV           (20 %) : Kein USV-Unit dem Rack zugeordnet
  - Shutdown-Lücken    (15 %) : Server ohne shutdown_priority
  - Keine PDU-Verb.    (10 %) : Server ohne verbundene PDU-Steckdose
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.domains.hardware.models import Device, PduOutlet, Rack


@dataclass
class RackAnomalyScore:
    rack_id: int
    rack_name: str
    score: float          # 0.0 – 1.0
    level: str            # 'ok' | 'warning' | 'critical'
    issues: list[str]


# Gewichte der Teilscores
_W_PHASE    = 0.25
_W_OVERLOAD = 0.30
_W_NO_USV   = 0.20
_W_SHUTDOWN = 0.15
_W_NO_PDU   = 0.10


def _level(score: float) -> str:
    if score < 0.30:
        return "ok"
    if score < 0.60:
        return "warning"
    return "critical"


def _effective_watt(dev: Device) -> float:
    """Bestimmt die effektive Leistungsaufnahme eines Geräts (in Watt)."""
    if dev.psu_nennwatt is not None:
        last_pct = float(dev.last_pct or 60.0)
        return float(dev.psu_nennwatt) * last_pct / 100.0
    if dev.tdp_watt is not None:
        return float(dev.tdp_watt)
    if dev.anschlussleistung_watt is not None:
        return float(dev.anschlussleistung_watt)
    return 0.0


class AnomalyScorer:
    """Berechnet Anomalie-Scores für alle Racks anhand dokumentierter Daten."""

    @staticmethod
    def score_all_racks(
        racks: Sequence[Rack],
        devices: Sequence[Device],
        outlets: Sequence[PduOutlet],
        usv_rack_ids: set[int],
    ) -> list[dict]:
        """
        Berechnet einen gewichteten Anomalie-Score für jedes Rack.

        Args:
            racks: Alle Rack-Objekte.
            devices: Alle Device-Objekte.
            outlets: Alle PduOutlet-Objekte (für PDU-Verbindungen).
            usv_rack_ids: Set von rack_ids, die mindestens ein USV-Unit haben.

        Returns:
            Liste von Dicts mit rack_id, rack_name, score (0–1), level, issues.
        """
        # Vorverarbeitung: Geräte pro Rack indexieren
        rack_devices: dict[int, list[Device]] = {}
        for dev in devices:
            if dev.rack_id is not None:
                rack_devices.setdefault(dev.rack_id, []).append(dev)

        # PDU-verbundene device_ids
        connected_device_ids: set[int] = {
            o.connected_device_id
            for o in outlets
            if o.connected_device_id is not None
        }

        results: list[dict] = []

        for rack in racks:
            devs = rack_devices.get(rack.id, [])
            servers = [d for d in devs if d.typ == "server"]

            issues: list[str] = []
            partial_scores: list[float] = []

            # ── 1. Phasen-Imbalance (25%) ────────────────────────────────────
            phase_load: dict[str, float] = {"L1": 0.0, "L2": 0.0, "L3": 0.0}
            for dev in devs:
                watt = _effective_watt(dev)
                phase = dev.phase or "L1"
                if phase in phase_load:
                    phase_load[phase] += watt

            loaded_phases = [v for v in phase_load.values() if v > 0]
            if len(loaded_phases) >= 2:
                max_p = max(loaded_phases)
                min_p = min(loaded_phases)
                imbalance_score = (max_p - min_p) / max_p if max_p > 0 else 0.0
                imbalance_score = min(1.0, imbalance_score)
                partial_scores.append(imbalance_score * _W_PHASE)
                delta_kw = round((max_p - min_p) / 1000, 2)
                max_phase = max(phase_load, key=lambda k: phase_load[k])
                min_phase = min(phase_load, key=lambda k: phase_load[k])
                if imbalance_score > 0.3:
                    issues.append(
                        f"Phasen-Imbalance: {max_phase}={round(phase_load[max_phase]/1000,1)} kW"
                        f" vs {min_phase}={round(phase_load[min_phase]/1000,1)} kW"
                        f" (Δ {delta_kw} kW)"
                    )
            else:
                partial_scores.append(0.0)

            # ── 2. Überlast vs. max_watt (30%) ───────────────────────────────
            total_watt = sum(_effective_watt(d) for d in devs)
            max_watt = float(rack.max_watt) if hasattr(rack, "max_watt") and rack.max_watt else None  # type: ignore[union-attr]
            if max_watt and max_watt > 0:
                overload_score = min(1.0, total_watt / max_watt)
                partial_scores.append(overload_score * _W_OVERLOAD)
                if overload_score > 0.85:
                    issues.append(
                        f"Überlast: {round(total_watt/1000,1)} kW von {round(max_watt/1000,1)} kW"
                        f" ({round(overload_score*100)}% Auslastung)"
                    )
                elif overload_score > 0.7:
                    issues.append(
                        f"Hohe Last: {round(total_watt/1000,1)} kW von {round(max_watt/1000,1)} kW"
                        f" ({round(overload_score*100)}%)"
                    )
            else:
                # Kein max_watt dokumentiert — kleiner Hinweis-Score
                partial_scores.append(0.1 * _W_OVERLOAD if total_watt > 0 else 0.0)
                if total_watt > 0 and not max_watt:
                    issues.append("Kein max_watt für Rack dokumentiert — Auslastung unbekannt")

            # ── 3. Kein USV (20%) ─────────────────────────────────────────────
            has_usv = rack.id in usv_rack_ids
            usv_score = 0.0 if has_usv else 1.0
            partial_scores.append(usv_score * _W_NO_USV)
            if not has_usv and servers:
                issues.append(f"Kein USV für dieses Rack dokumentiert ({len(servers)} Server betroffen)")

            # ── 4. Shutdown-Lücken (15%) ─────────────────────────────────────
            if servers:
                no_prio = [
                    s for s in servers
                    if s.shutdown_priority is None or s.shutdown_priority == 0
                ]
                shutdown_score = len(no_prio) / len(servers)
                partial_scores.append(shutdown_score * _W_SHUTDOWN)
                if no_prio:
                    issues.append(
                        f"{len(no_prio)} Server ohne Shutdown-Priorität"
                        f" ({', '.join(s.hostname for s in no_prio[:3])}{'…' if len(no_prio) > 3 else ''})"
                    )
            else:
                partial_scores.append(0.0)

            # ── 5. Keine PDU-Verbindung (10%) ─────────────────────────────────
            if servers:
                no_pdu = [s for s in servers if s.id not in connected_device_ids]
                pdu_score = len(no_pdu) / len(servers)
                partial_scores.append(pdu_score * _W_NO_PDU)
                if no_pdu:
                    issues.append(
                        f"{len(no_pdu)} Server ohne PDU-Steckdosen-Verbindung"
                        f" ({', '.join(s.hostname for s in no_pdu[:3])}{'…' if len(no_pdu) > 3 else ''})"
                    )
            else:
                partial_scores.append(0.0)

            total_score = round(sum(partial_scores), 3)
            total_score = max(0.0, min(1.0, total_score))

            results.append(
                RackAnomalyScore(
                    rack_id=rack.id,
                    rack_name=rack.name,
                    score=total_score,
                    level=_level(total_score),
                    issues=issues,
                ).__dict__
            )

        # Sortierung: kritischste zuerst
        results.sort(key=lambda r: r["score"], reverse=True)
        return results
