from dataclasses import dataclass
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Rack, Device, Cable, PduOutlet


@dataclass
class TopologyRaw:
    racks: Sequence[Rack]
    devices: Sequence[Device]
    cables: Sequence[Cable]
    outlets: Sequence[PduOutlet]
    dev_map: dict[int, Device]
    rack_map: dict[int, Rack]


async def load_topology(db: AsyncSession) -> TopologyRaw:
    racks = (
        (await db.execute(select(Rack).options(selectinload(Rack.devices))))
        .scalars()
        .all()
    )
    devices = (await db.execute(select(Device))).scalars().all()
    cables = (
        (
            await db.execute(
                select(Cable).options(
                    selectinload(Cable.von_device),
                    selectinload(Cable.nach_device),
                )
            )
        )
        .scalars()
        .all()
    )
    outlets = (await db.execute(select(PduOutlet))).scalars().all()

    return TopologyRaw(
        racks=racks,
        devices=devices,
        cables=cables,
        outlets=outlets,
        dev_map={d.id: d for d in devices},
        rack_map={r.id: r for r in racks},
    )


def build_edges(raw: TopologyRaw) -> list[dict]:
    edges = []
    for cable in raw.cables:
        if cable.von_device_id and cable.nach_device_id:
            vd = raw.dev_map.get(cable.von_device_id)
            nd = raw.dev_map.get(cable.nach_device_id)
            cross_rack = bool(
                vd and nd and vd.rack_id and nd.rack_id and vd.rack_id != nd.rack_id
            )
            edges.append({
                "id": f"cable-{cable.id}",
                "edge_type": "cable",
                "kabel_nr": cable.kabel_nr,
                "typ": cable.typ,
                "laenge_m": float(cable.laenge_m),
                "farbe": cable.farbe,
                "von_device_id": cable.von_device_id,
                "von_port": cable.von_port,
                "nach_device_id": cable.nach_device_id,
                "nach_port": cable.nach_port,
                "cross_rack": cross_rack,
            })

    for outlet in raw.outlets:
        if outlet.pdu_id and outlet.connected_device_id:
            pdu = raw.dev_map.get(outlet.pdu_id)
            dev = raw.dev_map.get(outlet.connected_device_id)
            cross_rack = bool(
                pdu and dev and pdu.rack_id and dev.rack_id and pdu.rack_id != dev.rack_id
            )
            edges.append({
                "id": f"power-{outlet.id}",
                "edge_type": "power",
                "kabel_nr": outlet.outlet_name,
                "typ": f"Strom-{outlet.steckdosentyp or 'PDU'}",
                "laenge_m": None,
                "farbe": None,
                "von_device_id": outlet.pdu_id,
                "von_port": outlet.outlet_name,
                "nach_device_id": outlet.connected_device_id,
                "nach_port": outlet.connected_port,
                "cross_rack": cross_rack,
                "phase": outlet.phase,
            })

    return edges


def build_racks_out(raw: TopologyRaw) -> list[dict]:
    return [
        {"id": r.id, "name": r.name, "standort": r.standort, "hoehe_u": r.hoehe_u}
        for r in raw.racks
    ]
