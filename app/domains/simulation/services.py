from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from collections import defaultdict

from app.domains.hardware.models import Device, DeviceDependency
from app.domains.simulation.schemas import SimulationScenario, SimulationResult, AffectedDevice, TimelineEvent

async def validate_no_cycles(session: AsyncSession, device_id: int, depends_on_ids: List[int]) -> bool:
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


async def run_simulation(session: AsyncSession, scenario: SimulationScenario) -> SimulationResult:
    messages = []
    
    # 1. Fetch devices with their outlets and dependencies
    stmt = select(Device).options(
        selectinload(Device.connected_pdu_outlets),
        selectinload(Device.dependencies)
    )
    res = await session.execute(stmt)
    devices = res.scalars().all()

    # Track states: "green", "yellow", "red"
    device_states = {d.id: "green" for d in devices}
    device_reasons = defaultdict(list)
    
    # 2. Simulate Power Loss
    if scenario.target_type == "phase":
        failed_phase = scenario.target_name
        messages.append(f"Simulating power loss on phase {failed_phase}")
        
        for dev in devices:
            if dev.typ in ["pdu", "usv"]:
                continue # Skip infrastructure for now, focus on consumers
                
            outlets = dev.connected_pdu_outlets
            if not outlets:
                continue
                
            active_psus = 0
            lost_psus = 0
            for outlet in outlets:
                # If the outlet phase matches the failed phase, it loses power
                if outlet.phase == failed_phase:
                    lost_psus += 1
                else:
                    active_psus += 1
                    
            if lost_psus > 0:
                if active_psus > 0:
                    device_states[dev.id] = "yellow"
                    device_reasons[dev.id].append(f"Lost redundant PSU on phase {failed_phase}")
                else:
                    device_states[dev.id] = "red"
                    device_reasons[dev.id].append(f"Lost all power from phase {failed_phase}")
                    
    elif scenario.target_type == "pdu_outlet" and scenario.target_id:
        failed_outlet_id = scenario.target_id
        messages.append(f"Simulating power loss on outlet {failed_outlet_id}")
        
        for dev in devices:
            outlets = dev.connected_pdu_outlets
            if not outlets:
                continue
                
            active_psus = 0
            lost_psus = 0
            for outlet in outlets:
                if outlet.id == failed_outlet_id:
                    lost_psus += 1
                else:
                    active_psus += 1
                    
            if lost_psus > 0:
                if active_psus > 0:
                    device_states[dev.id] = "yellow"
                    device_reasons[dev.id].append(f"Lost redundant power from outlet {failed_outlet_id}")
                else:
                    device_states[dev.id] = "red"
                    device_reasons[dev.id].append(f"Lost all power from outlet {failed_outlet_id}")
    
    # Add Network logic, etc. based on scenario...
    
    # 3. Calculate dependent failures (if A is red, what happens to B?)
    # A device dies if its required dependencies are all red (or based on HA logic)
    changed = True
    while changed:
        changed = False
        for dev in devices:
            if device_states[dev.id] == "red":
                continue # already dead
                
            deps = dev.dependencies
            if not deps:
                continue
                
            # Group by dependency_group
            groups = defaultdict(list)
            for d in deps:
                g = d.dependency_group or f"single_{d.depends_on_device_id}"
                groups[g].append(d.depends_on_device_id)
                
            # If ANY group is entirely RED, this device fails
            failed_groups = []
            for g_name, member_ids in groups.items():
                all_red = all(device_states.get(m_id) == "red" for m_id in member_ids)
                if all_red:
                    failed_groups.append(g_name)
                    
            if failed_groups:
                device_states[dev.id] = "red"
                device_reasons[dev.id].append(f"Lost dependencies: {', '.join(failed_groups)}")
                changed = True

    # 4. Gather affected devices
    affected = []
    for d_id, state in device_states.items():
        if state != "green":
            affected.append(AffectedDevice(
                device_id=d_id,
                state=state,
                reasons=device_reasons[d_id]
            ))

    # 5. Build Shutdown Timeline
    shutdown_timeline = _build_shutdown_timeline(devices, device_states)
    
    # 6. Build Boot Timeline
    boot_timeline = _build_boot_timeline(devices, device_states)

    return SimulationResult(
        affected_devices=affected,
        shutdown_timeline=shutdown_timeline,
        boot_timeline=boot_timeline,
        usv_battery_warning=False,
        messages=messages
    )


def _build_shutdown_timeline(devices: List[Device], states: Dict[int, str]) -> List[TimelineEvent]:
    timeline = []
    
    # We only shutdown things that are red (or we shutdown EVERYTHING if the scenario is a total datacenter loss)
    # For now, let's assume we build a sequence for all "red" devices
    red_devices = [d for d in devices if states[d.id] == "red"]
    
    # Sort by priority (1=highest priority to shutdown FIRST, 4=last)
    red_devices.sort(key=lambda d: (d.shutdown_priority or 2, d.shutdown_delay_seconds or 0))
    
    current_time = 0
    for d in red_devices:
        delay = d.shutdown_delay_seconds or 0
        current_time += delay
        method = d.shutdown_method or "ACPI_Graceful"
        
        timeline.append(TimelineEvent(
            time_seconds=current_time,
            device_id=d.id,
            action="shutdown",
            method=method,
            warning=False,
            message=f"Shutting down {d.hostname} (Priority {d.shutdown_priority})"
        ))
        
    return timeline

def _build_boot_timeline(devices: List[Device], states: Dict[int, str]) -> List[TimelineEvent]:
    timeline = []
    red_devices = [d for d in devices if states[d.id] == "red"]
    
    # Boot sequence is reverse priority (4=boot first, 1=boot last)
    # Actually wait, DBs are usually 4 (boot first, shutdown last), App Servers are 2 (boot last, shutdown first)
    red_devices.sort(key=lambda d: (-(d.shutdown_priority or 2), d.shutdown_delay_seconds or 0))
    
    current_time = 0
    for d in red_devices:
        delay = d.shutdown_delay_seconds or 0
        current_time += delay
        
        timeline.append(TimelineEvent(
            time_seconds=current_time,
            device_id=d.id,
            action="boot",
            method="Power_On",
            warning=False,
            message=f"Booting {d.hostname} (Priority {d.shutdown_priority})"
        ))
        
    return timeline
