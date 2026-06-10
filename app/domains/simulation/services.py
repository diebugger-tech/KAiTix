from typing import List, Dict, Sequence
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from collections import defaultdict

from app.domains.hardware.models import Device, DeviceDependency, Rack, PduOutlet
from app.domains.simulation.schemas import (
    SimulationScenario,
    SimulationResult,
    AffectedDevice,
    TimelineEvent,
)


async def validate_no_cycles(
    session: AsyncSession, device_id: int, depends_on_ids: List[int]
) -> bool:
    if not depends_on_ids:
        return True
    if device_id in depends_on_ids:
        return False

    stmt = select(DeviceDependency)
    result = await session.execute(stmt)
    deps = result.scalars().all()

    graph = defaultdict(list)
    for d in deps:
        graph[d.device_id].append(d.depends_on_device_id)

    for p_id in depends_on_ids:
        graph[device_id].append(p_id)

    visited = set()
    rec_stack = set()

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    for node in list(graph.keys()):
        if node not in visited:
            if dfs(node):
                return False
    return True


async def run_simulation(
    session: AsyncSession, scenario: SimulationScenario
) -> SimulationResult:
    messages = []

    # 1. Fetch devices with outlets, dependencies, cables, and VMs
    stmt = select(Device).options(
        selectinload(Device.connected_pdu_outlets).selectinload(PduOutlet.pdu),
        selectinload(Device.dependencies),
        selectinload(Device.virtual_machines),
        selectinload(Device.cables_from),
        selectinload(Device.cables_to),
    )
    res = await session.execute(stmt)
    devices = res.scalars().all()

    # Track states
    device_states = {d.id: "green" for d in devices}
    device_reasons = defaultdict(list)

    # Pre-populate failed target
    if scenario.target_type == "device" and scenario.target_id:
        device_states[scenario.target_id] = "red"
        device_reasons[scenario.target_id].append("Primary failure target")
        messages.append(f"Simulating failure of device {scenario.target_id}")
    elif scenario.target_type == "pdu_path" and scenario.target_name:
        path_name = scenario.target_name
        messages.append(f"Simulating failure of power path {path_name}")
        for dev in devices:
            if dev.typ == "pdu" and dev.redundancy_path == path_name:
                device_states[dev.id] = "red"
                device_reasons[dev.id].append(f"PDU belongs to failed path {path_name}")

    # 2. Iterative cascading failure resolution
    changed = True
    while changed:
        changed = False
        for dev in devices:
            if device_states[dev.id] == "red":
                continue  # already dead

            new_state = device_states[dev.id]
            reasons = []

            # Check power
            outlets = dev.connected_pdu_outlets
            if outlets:
                active_psus = 0
                lost_psus = 0
                for outlet in outlets:
                    outlet_lost = False
                    if (
                        scenario.target_type == "phase"
                        and outlet.phase == scenario.target_name
                    ):
                        outlet_lost = True
                    elif (
                        scenario.target_type == "pdu_outlet"
                        and outlet.id == scenario.target_id
                    ):
                        outlet_lost = True
                    elif outlet.pdu_id and device_states.get(outlet.pdu_id) == "red":
                        outlet_lost = True
                    elif scenario.target_type == "pdu_path" and (
                        outlet.redundancy_path == scenario.target_name
                        or (
                            outlet.pdu
                            and outlet.pdu.redundancy_path == scenario.target_name
                        )
                    ):
                        outlet_lost = True

                    if outlet_lost:
                        lost_psus += 1
                    else:
                        active_psus += 1

                if lost_psus > 0:
                    if active_psus > 0 and new_state == "green":
                        new_state = "yellow"
                        reasons.append("Lost redundant power")
                    elif active_psus == 0:
                        new_state = "red"
                        reasons.append("Lost all power")

            # Check network isolation
            net_cables = [
                c
                for c in (dev.cables_from + dev.cables_to)
                if c.typ and not str(c.typ).startswith("Strom")
            ]
            if net_cables:
                active_net = 0
                lost_net = 0
                for cable in net_cables:
                    peer_id = (
                        cable.nach_device_id
                        if cable.von_device_id == dev.id
                        else cable.von_device_id
                    )
                    if not peer_id:
                        continue
                    if device_states.get(peer_id) == "red":
                        lost_net += 1
                    else:
                        active_net += 1

                if lost_net > 0 and active_net == 0:
                    new_state = "red"
                    reasons.append("Network isolated: lost all upstream connections")

            # Check device dependencies
            deps = dev.dependencies
            if deps and new_state != "red":
                groups = defaultdict(list)
                for d in deps:
                    g = d.dependency_group or f"single_{d.depends_on_device_id}"
                    groups[g].append(d.depends_on_device_id)

                failed_groups = []
                for g_name, member_ids in groups.items():
                    if all(device_states.get(m_id) == "red" for m_id in member_ids):
                        failed_groups.append(g_name)

                if failed_groups:
                    new_state = "red"
                    reasons.append(f"Lost dependencies: {', '.join(failed_groups)}")

            # Update state if worsened
            if new_state != device_states[dev.id]:
                device_states[dev.id] = new_state
                device_reasons[dev.id].extend(reasons)
                changed = True

    # 3. Process VMs
    from app.domains.hardware.models import VirtualMachine
    from app.domains.runbooks.models import Runbook

    stmt_vms = select(VirtualMachine)
    res_vms = await session.execute(stmt_vms)
    vms = res_vms.scalars().all()

    vm_states = {v.id: "green" for v in vms}
    vm_reasons = defaultdict(list)

    vm_changed = True
    while vm_changed:
        vm_changed = False
        for vm in vms:
            if vm_states[vm.id] == "red":
                continue

            new_state = vm_states[vm.id]
            reasons = []

            # Host failure
            if vm.host_device_id and device_states.get(vm.host_device_id) == "red":
                new_state = "red"
                reasons.append("Host device failed")

            # Dependent VM failure
            if vm.depends_on_vm_id and vm_states.get(vm.depends_on_vm_id) == "red":
                new_state = "red"
                reasons.append(f"Dependent VM ({vm.depends_on_vm_id}) failed")

            if new_state != vm_states[vm.id]:
                vm_states[vm.id] = new_state
                vm_reasons[vm.id].extend(reasons)
                vm_changed = True

    # 4. Gather affected entities
    affected_devs = []
    affected_vms_list = []
    from app.domains.simulation.schemas import AffectedVM, AffectedRunbook

    for d_id, state in device_states.items():
        if state != "green":
            affected_devs.append(
                AffectedDevice(
                    device_id=d_id, state=state, reasons=list(set(device_reasons[d_id]))
                )
            )

    for v_id, state in vm_states.items():
        if state != "green":
            affected_vms_list.append(
                AffectedVM(vm_id=v_id, state=state, reasons=list(set(vm_reasons[v_id])))
            )

    # 5. Check Runbook Impact
    affected_runbooks = []
    if affected_devs or affected_vms_list:
        red_dev_ids = [d.device_id for d in affected_devs if d.state == "red"]
        red_vm_ids = [v.vm_id for v in affected_vms_list if v.state == "red"]

        stmt_rb = select(Runbook).options(selectinload(Runbook.devices))
        res_rb = await session.execute(stmt_rb)
        runbooks = res_rb.scalars().unique().all()

        for rb in runbooks:
            rb_reasons = []
            for rd in rb.devices:
                if rd.device_id and rd.device_id in red_dev_ids:
                    rb_reasons.append(f"Contains failed device ID {rd.device_id}")
                if rd.vm_id and rd.vm_id in red_vm_ids:
                    rb_reasons.append(f"Contains failed VM ID {rd.vm_id}")
            if rb_reasons:
                affected_runbooks.append(
                    AffectedRunbook(runbook_id=rb.id, reasons=list(set(rb_reasons)))
                )

    # Build Timelines (using original logic)
    shutdown_timeline = _build_shutdown_timeline(devices, device_states)  # type: ignore
    boot_timeline = _build_boot_timeline(devices, device_states)  # type: ignore

    return SimulationResult(
        affected_devices=affected_devs,
        affected_vms=affected_vms_list,
        affected_runbooks=affected_runbooks,
        shutdown_timeline=shutdown_timeline,
        boot_timeline=boot_timeline,
        usv_battery_warning=False,
        messages=messages,
    )


def _build_shutdown_timeline(
    devices: List[Device], states: Dict[int, str]
) -> List[TimelineEvent]:
    timeline = []

    # We only shutdown things that are red (or we shutdown EVERYTHING if the scenario is a total datacenter loss)
    # For now, let's assume we build a sequence for all "red" devices
    red_devices = [d for d in devices if states[d.id] == "red"]

    # Sort by priority (1=highest priority to shutdown FIRST, 4=last)
    red_devices.sort(
        key=lambda d: (d.shutdown_priority or 2, d.shutdown_delay_seconds or 0)
    )

    current_time = 0
    for d in red_devices:
        delay = d.shutdown_delay_seconds or 0
        current_time += delay
        method = d.shutdown_method or "ACPI_Graceful"

        timeline.append(
            TimelineEvent(
                time_seconds=current_time,
                device_id=d.id,
                action="shutdown",
                method=method,
                warning=False,
                message=f"Shutting down {d.hostname} (Priority {d.shutdown_priority})",
            )
        )

    return timeline


def _build_boot_timeline(
    devices: List[Device], states: Dict[int, str]
) -> List[TimelineEvent]:
    timeline = []
    red_devices = [d for d in devices if states[d.id] == "red"]

    # Boot sequence is reverse priority (4=boot first, 1=boot last)
    # Actually wait, DBs are usually 4 (boot first, shutdown last), App Servers are 2 (boot last, shutdown first)
    red_devices.sort(
        key=lambda d: (-(d.shutdown_priority or 2), d.shutdown_delay_seconds or 0)
    )

    current_time = 0
    for d in red_devices:
        delay = d.shutdown_delay_seconds or 0
        current_time += delay

        timeline.append(
            TimelineEvent(
                time_seconds=current_time,
                device_id=d.id,
                action="boot",
                method="Power_On",
                warning=False,
                message=f"Booting {d.hostname} (Priority {d.shutdown_priority})",
            )
        )

    return timeline


@dataclass
class RackAnomalyScore:
    rack_id: int
    rack_name: str
    score: float  # 0.0 – 1.0
    level: str  # 'ok' | 'warning' | 'critical'
    issues: list[str]


# Gewichte der Teilscores
_W_PHASE = 0.25
_W_OVERLOAD = 0.30
_W_NO_USV = 0.20
_W_SHUTDOWN = 0.15
_W_NO_PDU = 0.10
_W_PDU_REDUNDANCY = 0.20


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
            o.connected_device_id for o in outlets if o.connected_device_id is not None
        }

        # Outlets pro Gerät indexieren
        dev_outlets: dict[int, list[PduOutlet]] = {}
        for o in outlets:
            if o.connected_device_id is not None:
                dev_outlets.setdefault(o.connected_device_id, []).append(o)

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
                        f"Phasen-Imbalance: {max_phase}={round(phase_load[max_phase] / 1000, 1)} kW"
                        f" vs {min_phase}={round(phase_load[min_phase] / 1000, 1)} kW"
                        f" (Δ {delta_kw} kW)"
                    )
            else:
                partial_scores.append(0.0)

            # ── 2. Überlast vs. max_watt (30%) ───────────────────────────────
            total_watt = sum(_effective_watt(d) for d in devs)
            max_watt = (
                float(rack.max_watt)
                if hasattr(rack, "max_watt") and rack.max_watt
                else None
            )  # type: ignore[union-attr]
            if max_watt and max_watt > 0:
                overload_score = min(1.0, total_watt / max_watt)
                partial_scores.append(overload_score * _W_OVERLOAD)
                if overload_score > 0.85:
                    issues.append(
                        f"Überlast: {round(total_watt / 1000, 1)} kW von {round(max_watt / 1000, 1)} kW"
                        f" ({round(overload_score * 100)}% Auslastung)"
                    )
                elif overload_score > 0.7:
                    issues.append(
                        f"Hohe Last: {round(total_watt / 1000, 1)} kW von {round(max_watt / 1000, 1)} kW"
                        f" ({round(overload_score * 100)}%)"
                    )
            else:
                # Kein max_watt dokumentiert — kleiner Hinweis-Score
                partial_scores.append(0.1 * _W_OVERLOAD if total_watt > 0 else 0.0)
                if total_watt > 0 and not max_watt:
                    issues.append(
                        "Kein max_watt für Rack dokumentiert — Auslastung unbekannt"
                    )

            # ── 3. Kein USV (20%) ─────────────────────────────────────────────
            has_usv = rack.id in usv_rack_ids
            usv_score = 0.0 if has_usv else 1.0
            partial_scores.append(usv_score * _W_NO_USV)
            if not has_usv and servers:
                issues.append(
                    f"Kein USV für dieses Rack dokumentiert ({len(servers)} Server betroffen)"
                )

            # ── 4. Shutdown-Lücken (15%) ─────────────────────────────────────
            if servers:
                no_prio = [
                    s
                    for s in servers
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

            # ── 6. PDU-Spezifische Prüfungen (Höhe, Kapazität, Redundanz, Schieflast) ─
            rack_pdus = [d for d in devs if d.typ == "pdu"]
            pdu_redundancy_score = 0.0

            # 6a - Falsche PDU für Rack-Höhe
            for pdu in rack_pdus:
                if pdu.min_rack_hoehe and pdu.min_rack_hoehe > rack.hoehe_u:
                    pdu_redundancy_score = max(pdu_redundancy_score, 0.3)
                    issues.append(
                        f"PDU {pdu.hostname} inkompatibel: Benötigt min. {pdu.min_rack_hoehe} HE, Rack hat nur {rack.hoehe_u} HE"
                    )

            # 6b - PDU-Kapazität vs. Rack-Last (Pfadausfall)
            pdu_a = next((p for p in rack_pdus if p.redundancy_path == "A"), None)
            pdu_b = next((p for p in rack_pdus if p.redundancy_path == "B"), None)

            # 6d - Pfad-Schieflast (A vs B)
            a_load = 0.0
            b_load = 0.0
            for d in devs:
                if d.typ in ("server", "switch", "storage", "firewall"):
                    connected_outlets = dev_outlets.get(d.id, [])
                    paths = [
                        o.redundancy_path
                        for o in connected_outlets
                        if o.redundancy_path in ("A", "B")
                    ]
                    if paths:
                        d_watt = _effective_watt(d)
                        for path in paths:
                            if path == "A":
                                a_load += d_watt / len(paths)
                            elif path == "B":
                                b_load += d_watt / len(paths)

            def get_pdu_capacity_watts(pdu):
                if not pdu.absicherung_a:
                    return 0.0
                amps = float(pdu.absicherung_a)
                volts = float(pdu.spannung_v or 230)
                phases = 3 if pdu.strom_typ == "3-phasig" else 1
                factor = 1.73205 if phases == 3 else 1.0
                return amps * volts * factor * 0.8  # 80% continuous load limit

            if pdu_a:
                cap_a = get_pdu_capacity_watts(pdu_a)
                if cap_a > 0.0:
                    if total_watt > cap_a:
                        pdu_redundancy_score = max(pdu_redundancy_score, 0.8)
                        issues.append(
                            f"Überlast-Risiko: Last ({round(total_watt / 1000, 2)} kW) überschreitet PDU-A Kapazität ({round(cap_a / 1000, 2)} kW) bei Ausfall von Pfad B"
                        )
                    elif a_load > cap_a * 0.5:
                        pdu_redundancy_score = max(pdu_redundancy_score, 0.4)
                        issues.append(
                            f"Pfad A Auslastung: {round(a_load / 1000, 2)} kW überschreitet 50% der PDU-Kapazität ({round(cap_a / 1000, 2)} kW) - Überlast bei Umschaltung droht"
                        )
            if pdu_b:
                cap_b = get_pdu_capacity_watts(pdu_b)
                if cap_b > 0.0:
                    if total_watt > cap_b:
                        pdu_redundancy_score = max(pdu_redundancy_score, 0.8)
                        issues.append(
                            f"Überlast-Risiko: Last ({round(total_watt / 1000, 2)} kW) überschreitet PDU-B Kapazität ({round(cap_b / 1000, 2)} kW) bei Ausfall von Pfad A"
                        )
                    elif b_load > cap_b * 0.5:
                        pdu_redundancy_score = max(pdu_redundancy_score, 0.4)
                        issues.append(
                            f"Pfad B Auslastung: {round(b_load / 1000, 2)} kW überschreitet 50% der PDU-Kapazität ({round(cap_b / 1000, 2)} kW) - Überlast bei Umschaltung droht"
                        )

            # 6c - Dual-PSU Redundanz
            redundant_failures = 0
            for server in servers:
                if server.psu_count and server.psu_count >= 2:
                    connected_outlets = dev_outlets.get(server.id, [])
                    paths = {  # type: ignore
                        o.redundancy_path
                        for o in connected_outlets
                        if o.redundancy_path in ("A", "B")
                    }
                    if len(paths) < 2:
                        redundant_failures += 1
                        issues.append(
                            f"Redundanz-Fehler: Server {server.hostname} hat {server.psu_count} PSUs, aber keine A/B-Redundanz"
                        )
            if redundant_failures > 0:
                pdu_redundancy_score = max(pdu_redundancy_score, 0.6)

            # 6d - Pfad-Schieflast (A vs B)
            if a_load > 0.0 and b_load > 0.0:
                max_l = max(a_load, b_load)
                imbalance = abs(a_load - b_load) / max_l if max_l > 0 else 0.0
                if imbalance > 0.20:
                    pdu_redundancy_score = max(pdu_redundancy_score, 0.3)
                    issues.append(
                        f"Pfad-Schieflast: Pfad A ({round(a_load / 1000, 2)} kW) vs Pfad B ({round(b_load / 1000, 2)} kW) weicht um {round(imbalance * 100)}% ab"
                    )

            partial_scores.append(pdu_redundancy_score * _W_PDU_REDUNDANCY)

            # ── 7. Logische Fehler (Doku-Inkonsistenzen) ──────────────────────
            logical_errors_score = 0.0

            # 7a - U-Positions-Konflikte (HE-Überlappung)
            rack_u_slots: dict[int, list[Device]] = {}
            for dev in devs:
                if getattr(dev, "side", None) is not None:
                    continue  # Zero-U Geräte ignorieren
                u_pos = getattr(dev, "u_position", None)
                u_h = getattr(dev, "u_hoehe", 1) or 1
                if u_pos is not None and u_h > 0:
                    for u in range(u_pos, u_pos + u_h):
                        if u in rack_u_slots:
                            for c_dev in rack_u_slots[u]:
                                issues.append(
                                    f"HE-Konflikt auf HE {u}: {dev.hostname} überlappt mit {c_dev.hostname}"
                                )
                                logical_errors_score = max(logical_errors_score, 0.5)
                            rack_u_slots[u].append(dev)
                        else:
                            rack_u_slots[u] = [dev]

            # 7b - Fehlende Phase bei Stromverbrauchern
            for dev in devs:
                tdp = _effective_watt(dev)
                phase = getattr(dev, "phase", None)
                strom_typ = getattr(dev, "strom_typ", None)
                if tdp > 0 and phase is None and strom_typ != "3-phasig":
                    issues.append(
                        f"Logik-Fehler: {dev.hostname} hat {round(tdp, 1)}W Verbrauch, aber keine Phase (L1/L2/L3) dokumentiert"
                    )
                    logical_errors_score = max(logical_errors_score, 0.2)

            partial_scores.append(logical_errors_score)

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
